import re
import zipfile
import xml.etree.ElementTree as ET
from typing import Optional

from calibre.utils.logging import default_log

from .base import BaseDetector, DetectionResult, UNDETECTED

_NCX_NS       = 'http://www.daisy.org/z3986/2005/ncx/'
_OPF_NS       = 'http://www.idpf.org/2007/opf'
_CONTAINER    = 'META-INF/container.xml'
_CONTAINER_NS = 'urn:oasis:names:tc:opendocument:xmlns:container'

# Regex patterns used on raw XHTML bytes to avoid HTML-entity XML parse failures.
# nav.xhtml and spine content files regularly contain &nbsp;, &mdash;, etc.
_RE_NAV_TOC = re.compile(
    rb'<nav\b[^>]*epub:type=["\'][^"\']*toc[^"\']*["\'][^>]*>(.*?)</nav>',
    re.DOTALL | re.IGNORECASE,
)
_RE_LI = re.compile(rb'<li\b', re.IGNORECASE)


class EpubDetector(BaseDetector):

    def detect(self, book_path: str, per_book_config: dict) -> DetectionResult:
        try:
            return self._detect(book_path, per_book_config)
        except Exception:
            import traceback
            default_log.error(f'EpubDetector failed on {book_path}:\n{traceback.format_exc()}')
            return UNDETECTED

    def _detect(self, book_path: str, cfg: dict) -> DetectionResult:
        force          = cfg.get('force_method')
        use_toc        = cfg.get('epub_use_toc', True)
        use_structural = cfg.get('epub_use_structural', True)
        heading_tags   = cfg.get('epub_heading_tags', ['h1', 'h2'])

        with zipfile.ZipFile(book_path, 'r') as zf:
            names = zf.namelist()

            if force != 'structural' and use_toc:
                result = self._try_toc(zf, names)
                if result is not None and result.count > 0:
                    return result
                if force == 'toc':
                    return UNDETECTED

            if force != 'toc' and use_structural:
                result = self._try_structural(zf, names, heading_tags)
                if result is not None and result.count > 0:
                    return result

        return UNDETECTED

    def _try_toc(self, zf: zipfile.ZipFile, names: list) -> Optional[DetectionResult]:
        # EPUB2: toc.ncx is pure XML — ET is safe here
        ncx_path = next((n for n in names if n.endswith('toc.ncx')), None)
        if ncx_path:
            try:
                root    = ET.fromstring(zf.read(ncx_path))
                nav_map = root.find(f'{{{_NCX_NS}}}navMap')
                if nav_map is not None:
                    top = nav_map.findall(f'{{{_NCX_NS}}}navPoint')
                    if top:
                        return DetectionResult(count=len(top), method='toc', confidence='high')
            except ET.ParseError:
                pass

        # EPUB3: nav.xhtml is XHTML and may contain HTML entities — use regex
        nav_path = next(
            (n for n in names if n.endswith('nav.xhtml') or n.endswith('nav.htm')), None
        )
        if nav_path:
            count = self._count_nav_items(zf.read(nav_path))
            if count > 0:
                return DetectionResult(count=count, method='toc', confidence='high')

        return None

    @staticmethod
    def _count_nav_items(data: bytes) -> int:
        m = _RE_NAV_TOC.search(data)
        return len(_RE_LI.findall(m.group(1))) if m else 0

    def _try_structural(
        self, zf: zipfile.ZipFile, names: list, heading_tags: list
    ) -> Optional[DetectionResult]:
        if _CONTAINER not in names:
            return None
        try:
            container_root = ET.fromstring(zf.read(_CONTAINER))
        except ET.ParseError:
            return None

        opf_path_el = container_root.find(f'.//{{{_CONTAINER_NS}}}rootfile')
        if opf_path_el is None:
            return None
        opf_path = opf_path_el.get('full-path', '')
        if opf_path not in names:
            return None

        try:
            opf_root = ET.fromstring(zf.read(opf_path))
        except ET.ParseError:
            return None

        opf_dir  = opf_path.rsplit('/', 1)[0] if '/' in opf_path else ''
        spine    = opf_root.find(f'{{{_OPF_NS}}}spine')
        manifest = opf_root.find(f'{{{_OPF_NS}}}manifest')
        if spine is None or manifest is None:
            return None

        id_to_href = {
            item.get('id'): item.get('href', '')
            for item in manifest.findall(f'{{{_OPF_NS}}}item')
        }

        # Search raw bytes for heading tags — immune to HTML entities in XHTML content
        tags_pat   = '|'.join(re.escape(t) for t in heading_tags)
        heading_re = re.compile(rf'<(?:{tags_pat})\b'.encode(), re.IGNORECASE)

        count = 0
        for itemref in spine.findall(f'{{{_OPF_NS}}}itemref'):
            href      = id_to_href.get(itemref.get('idref', ''), '')
            full_path = f'{opf_dir}/{href}' if opf_dir else href
            if full_path not in names:
                continue
            count += len(heading_re.findall(zf.read(full_path)))

        return DetectionResult(count=count, method='structural', confidence='medium') if count else None
