"""Local PDF -> math-aware OCR -> Markdown -> standalone XeLaTeX.

No hosted OCR or paid API. Run --help or --doctor before converting.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
from importlib.metadata import version, PackageNotFoundError
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

DEFAULT_OUTPUT = Path(__file__).resolve().parent / 'output'

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, 'reconfigure'):
        _stream.reconfigure(encoding='utf-8', errors='replace')


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def doctor():
    result = {'python': sys.version, 'xelatex': shutil.which('xelatex')}
    for name in ('marker', 'torch', 'pypandoc'):
        result[name] = importlib.util.find_spec(name) is not None
    if result['pypandoc']:
        import pypandoc
        try:
            result['pandoc'] = pypandoc.get_pandoc_path()
        except OSError as exc:
            result['pandoc_error'] = str(exc)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if all(result[n] for n in ('marker', 'torch', 'pypandoc')) and result.get('pandoc') else 2


def select_content(markdown, job):
    # Exact source text anchors; never infer geometry from keywords or renumber.
    start, end = job.get('start'), job.get('end')
    if start:
        if markdown.count(start) != 1:
            raise ValueError(f'Start anchor must occur exactly once: {start!r}')
        markdown = markdown[markdown.index(start):]
    if end:
        if markdown.count(end) != 1:
            raise ValueError(f'End anchor must occur exactly once: {end!r}')
        markdown = markdown[:markdown.index(end)]
    for cut in job.get('exclude', []):
        a, b = cut['start'], cut['end']
        if markdown.count(a) != 1 or markdown.count(b) != 1:
            raise ValueError(f'Exclusion anchors missing or ambiguous: {a!r}, {b!r}')
        i, j = markdown.index(a), markdown.index(b)
        if j <= i:
            raise ValueError('Exclusion end must follow start')
        markdown = markdown[:i] + markdown[j:]
    if not markdown.strip():
        raise ValueError('Selected content is empty')
    return markdown


def warnings_for(text):
    warnings = ['OCR output requires comparison with the source PDF; compilation is not content validation.']
    for pattern, message in (
        (r'\(cid:\d+\)|\ufffd', 'Broken character encoding detected'),
        (r'<table\b', 'Raw HTML table detected: inspect its conversion carefully'),
        (r'!\[', 'Images present: some content may remain as an image'),
    ):
        if re.search(pattern, text, re.I):
            warnings.append(message)
    if len(text.strip()) < 80:
        warnings.append('Very little text was recognized')
    return warnings


def compile_tex(tex, timeout):
    executable = shutil.which('xelatex')
    if not executable:
        raise RuntimeError('XeLaTeX not found. Install MiKTeX/TeX Live and restart the terminal.')
    for _ in range(2):
        run = subprocess.run(
            [executable, '-no-shell-escape', '-interaction=nonstopmode',
             '-halt-on-error', tex.name], cwd=tex.parent,
            capture_output=True, timeout=timeout,
        )
        (tex.parent / 'build-output.txt').write_bytes(run.stdout + run.stderr)
        if run.returncode:
            raise RuntimeError(f'XeLaTeX failed; inspect {tex.parent / "build-output.txt"}')
    return 'success'


def to_tex(markdown, directory):
    import pypandoc
    # Pandoc handles escaping, lists, math, tables and image paths; no regex
    # conversion of formulas, no generated replacement solutions.
    source = directory / 'selected.md'
    source.write_text(markdown, encoding='utf-8')
    tex = directory / 'document.tex'
    pypandoc.convert_file(str(source), 'latex',
        format='markdown+tex_math_dollars+tex_math_single_backslash+raw_tex',
        outputfile=str(tex), extra_args=[
            '--standalone', '--wrap=none', '--pdf-engine=xelatex',
            '-V', 'mainfont=Times New Roman', '-V', 'geometry:margin=2cm',
            '-V', 'fontsize=12pt', '-V', 'papersize=a4',
            '--resource-path=' + str(directory),
        ])
    tex.write_text('% !TeX program = xelatex\n' + tex.read_text(encoding='utf-8'), encoding='utf-8')
    return tex


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', nargs='?', type=Path, help='PDF or folder (recursive)')
    parser.add_argument('--output', type=Path, default=DEFAULT_OUTPUT,
                        help='Output folder (default: output beside convert.py)')
    parser.add_argument('--manifest', type=Path, help='Explicit jobs, page ranges and exclusion anchors')
    parser.add_argument('--doctor', action='store_true')
    parser.add_argument('--plan', action='store_true', help='List validated jobs without loading OCR models')
    parser.add_argument('--device', choices=['cpu', 'cuda'], default='cpu')
    parser.add_argument('--compile', action='store_true', help='Also run local XeLaTeX')
    parser.add_argument('--timeout', type=int, default=600, help='Compilation timeout in seconds')
    parser.add_argument('--limit', type=int, help='Process first N PDFs/jobs')
    parser.add_argument('--from-markdown', type=Path, help='Test/rebuild TeX from reviewed Markdown without OCR')
    args = parser.parse_args(argv)
    if args.doctor:
        return doctor()
    if args.from_markdown:
        if not args.from_markdown.is_file():
            parser.error('Markdown input does not exist')
        destination = args.output.resolve()
        if destination.exists():
            parser.error('Output folder already exists; choose a new folder')
        destination.mkdir(parents=True)
        tex = to_tex(args.from_markdown.read_text(encoding='utf-8'), destination)
        if args.compile:
            compile_tex(tex, args.timeout)
        print(tex)
        return 0
    if not args.input:
        try:
            supplied = input('Nhập đường dẫn file PDF: ').strip().strip('"')
        except (EOFError, KeyboardInterrupt):
            parser.error('Provide a PDF path as an argument or at the prompt')
        if not supplied:
            parser.error('PDF path cannot be empty')
        args.input = Path(supplied)
    if not args.input.exists():
        parser.error('Provide an existing PDF or input folder')
    root = args.input.resolve()
    base = root if root.is_dir() else root.parent
    out = args.output.resolve()
    if out == base or out.is_relative_to(base):
        parser.error('Output must be outside the source folder')
    if args.manifest:
        jobs = json.loads(args.manifest.read_text(encoding='utf-8'))['jobs']
    else:
        pdfs = sorted(root.rglob('*.pdf')) if root.is_dir() else [root]
        jobs = [{'pdf': str(p.relative_to(base)),
                 'output': str(p.relative_to(base).with_suffix(''))} for p in pdfs]
    if args.limit is not None:
        if args.limit < 1:
            parser.error('--limit must be positive')
        jobs = jobs[:args.limit]
    if not jobs:
        parser.error('No PDFs/jobs found')
    # Validate every path before loading models or creating output files.
    targets = set()
    for job in jobs:
        pdf = (base / job['pdf']).resolve()
        target = (out / job['output']).resolve()
        if not pdf.is_relative_to(base) or not pdf.is_file() or pdf.suffix.lower() != '.pdf':
            parser.error(f'Invalid source PDF: {pdf}')
        if not target.is_relative_to(out) or target == out or target in targets or target.exists():
            parser.error(f'Output exists, duplicates another job or escapes output root: {target}')
        targets.add(target)
    if args.plan:
        print(json.dumps({'output_root': str(out), 'jobs': jobs}, ensure_ascii=False, indent=2))
        return 0
    missing = [name for name in ('marker', 'torch', 'pypandoc')
               if importlib.util.find_spec(name) is None]
    if missing:
        print('Missing dependencies: ' + ', '.join(missing)
              + '. Run this interpreter with: -m pip install -r requirements.txt', file=sys.stderr)
        return 2
    os.environ['TORCH_DEVICE'] = args.device
    from marker.converters.pdf import PdfConverter
    from marker.models import create_model_dict
    from marker.output import text_from_rendered
    from marker.config.parser import ConfigParser
    try:
        models = create_model_dict()
    except Exception as exc:
        print(f'Cannot load local OCR models: {exc}. Check Internet, free disk space and PyTorch installation.', file=sys.stderr)
        return 1
    report = []
    out.mkdir(parents=True, exist_ok=True)
    for index, job in enumerate(jobs, 1):
        pdf = (base / job['pdf']).resolve()
        target = (out / job['output']).resolve()
        target.mkdir(parents=True)
        row = {'source': str(pdf), 'sha256': digest(pdf), 'output': str(target),
               'config': job, 'status': 'running', 'content_verified': False}
        row['versions'] = {}
        for package in ('marker-pdf', 'surya-ocr', 'torch', 'pypandoc_binary'):
            try:
                row['versions'][package] = version(package)
            except PackageNotFoundError:
                row['versions'][package] = None
        print(f'[{index}/{len(jobs)}] {pdf}', flush=True)
        try:
            config = {'output_format': 'markdown', 'force_ocr': True,
                      'use_llm': False, 'keep_pageheader_in_output': True,
                      'keep_pagefooter_in_output': True, 'disable_multiprocessing': True}
            if job.get('pages'):
                config['page_range'] = job['pages']  # Marker uses zero-based pages.
            cp = ConfigParser(config)
            converter = PdfConverter(config=cp.generate_config_dict(),
                artifact_dict=models, processor_list=cp.get_processors(),
                renderer=cp.get_renderer())
            rendered = converter(str(pdf))
            markdown, _, images = text_from_rendered(rendered)
            (target / 'raw.md').write_text(markdown, encoding='utf-8')
            (target / 'metadata.json').write_text(
                json.dumps(rendered.metadata, ensure_ascii=False, indent=2, default=str), encoding='utf-8')
            for name, image in images.items():
                asset = (target / name).resolve()
                if not asset.is_relative_to(target):
                    raise ValueError('OCR image path escapes output directory')
                asset.parent.mkdir(parents=True, exist_ok=True)
                image.save(asset)
            selected = select_content(markdown, job)
            row['warnings'] = warnings_for(selected)
            tex = to_tex(selected, target)
            row['tex'] = str(tex)
            row['compile'] = compile_tex(tex, args.timeout) if args.compile else 'not_requested'
            row['status'] = 'converted_needs_review'
        except Exception as exc:
            row['status'] = 'failed'
            row['error'] = str(exc)
            print(f'ERROR: {exc}', file=sys.stderr, flush=True)
        report.append(row)
        (target / 'report.json').write_text(json.dumps(row, ensure_ascii=False, indent=2), encoding='utf-8')
        (out / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    return 1 if any(r['status'] == 'failed' for r in report) else 0


if __name__ == '__main__':
    raise SystemExit(main())
