import zipfile
import xml.etree.ElementTree as ET
from typing import Optional

from .base import BaseDetector, DetectionResult, UNDETECTED

_NCX_NS   = 'http://www.daisy.org/z3986/2005/ncx/'
_OPF_NS   = 'http://www.idpf.org/2007/opf'
_XHTML_NS = 'http://www.w3.org/1999/xhtml'
_EPUB_NS  = 'http://www.idpf.org/2007/ops'

_CONTAINER = 'META-INF/container.xml'
_CONTAINER_NS = 'urn:oasis:names:tc:opendocument:xmlns:container'


class EpubDetector(BaseDetector):

    def detect(self, book_path: str, per_book_config: dict) -> DetectionResult:
        try:
            return self._detect(book_path, per_book_config)
        except Exception:
            return UNDETECTED

    def _detect(self, book_path: str, cfg: dict) -> DetectionResult:
        force = cfg.get('force_method')
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
        # EPUB2: toc.ncx
        ncx_path = next((n for n in names if n.endswith('toc.ncx')), None)
        if ncx_path:
            root = ET.fromstring(zf.read(ncx_path))
            nav_map = root.find(f'{{{_NCX_NS}}}navMap')
            if nav_map is not None:
                top = nav_map.findall(f'{{{_NCX_NS}}}navPoint')
                if top:
                    return DetectionResult(count=len(top), method='toc', confidence='high')

        # EPUB3: nav.xhtml
        nav_path = next((n for n in names if n.endswith('nav.xhtml') or n.endswith('nav.htm')), None)
        if nav_path:
            root = ET.fromstring(zf.read(nav_path))
            for nav in root.iter(f'{{{_XHTML_NS}}}nav'):
                if 'toc' in nav.get(f'{{{_EPUB_NS}}}type', ''):
                    ol = nav.find(f'{{{_XHTML_NS}}}ol')
                    if ol is not None:
                        items = ol.findall(f'{{{_XHTML_NS}}}li')
                        if items:
                            return DetectionResult(count=len(items), method='toc', confidence='high')

        return None

    def _try_structural(self, zf: zipfile.ZipFile, names: list, heading_tags: list) -> Optional[DetectionResult]:
        if _CONTAINER not in names:
            return None
        container_root = ET.fromstring(zf.read(_CONTAINER))
        opf_path_el = container_root.find(f'.//{{{_CONTAINER_NS}}}rootfile')
        if opf_path_el is None:
            return None
        opf_path = opf_path_el.get('full-path', '')

        if opf_path not in names:
            return None
        opf_root  = ET.fromstring(zf.read(opf_path))
        opf_dir   = opf_path.rsplit('/', 1)[0] if '/' in opf_path else ''
        spine     = opf_root.find(f'{{{_OPF_NS}}}spine')
        manifest  = opf_root.find(f'{{{_OPF_NS}}}manifest')
        if spine is None or manifest is None:
            return None

        id_to_href = {
            item.get('id'): item.get('href', '')
            for item in manifest.findall(f'{{{_OPF_NS}}}item')
        }

        count = 0
        for itemref in spine.findall(f'{{{_OPF_NS}}}itemref'):
            href      = id_to_href.get(itemref.get('idref', ''), '')
            full_path = f'{opf_dir}/{href}' if opf_dir else href
            if full_path not in names:
                continue
            content_root = ET.fromstring(zf.read(full_path))
            for tag in heading_tags:
                count += len(content_root.findall(f'.//{{{_XHTML_NS}}}{tag}'))

        return DetectionResult(count=count, method='structural', confidence='medium') if count else None
