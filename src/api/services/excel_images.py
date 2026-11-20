"""Extract worksheet-anchored raster images through OOXML relationships."""
from dataclasses import dataclass, field
from io import BytesIO
from pathlib import Path
import posixpath
from xml.etree import ElementTree as ET
from zipfile import ZipFile

from PIL import Image, UnidentifiedImageError

from src.api.services.import_errors import DocumentImportError

REL = '{http://schemas.openxmlformats.org/officeDocument/2006/relationships}'
DRAW = '{http://schemas.openxmlformats.org/drawingml/2006/main}'
MIN_SIDE = 128
MIN_AREA = 40_000


@dataclass
class EmbeddedImage:
    data: bytes
    sheet: str
    extension: str
    mimetype: str


@dataclass
class ImageExtraction:
    images: list[EmbeddedImage] = field(default_factory=list)
    skipped: int = 0
    warnings: list[str] = field(default_factory=list)


def _relationships(archive, part):
    rels_path = posixpath.join(posixpath.dirname(part), '_rels', posixpath.basename(part) + '.rels')
    if rels_path not in archive.namelist():
        return {}
    relationships = {}
    for relation in ET.fromstring(archive.read(rels_path)):
        if relation.get('TargetMode') == 'External':
            continue
        target = relation.get('Target', '')
        resolved = (target.lstrip('/') if target.startswith('/') else
                    posixpath.normpath(posixpath.join(posixpath.dirname(part), target)))
        if resolved.startswith('../'):
            continue
        relationships[relation.get('Id')] = resolved
    return relationships


def extract_excel_images(path: Path) -> ImageExtraction:
    result = ImageExtraction()
    if path.suffix.lower() not in {'.xlsx', '.xlsm', '.xltx', '.xltm'}:
        return result
    extensions = {'PNG': '.png', 'JPEG': '.jpg', 'GIF': '.gif', 'BMP': '.bmp',
                  'TIFF': '.tiff', 'WEBP': '.webp'}
    try:
        with ZipFile(path) as archive:
            workbook_part = 'xl/workbook.xml'
            sheets = ET.fromstring(archive.read(workbook_part))
            workbook_rels = _relationships(archive, workbook_part)
            for sheet in sheets.findall('.//{*}sheet'):
                sheet_part = workbook_rels.get(sheet.get(REL + 'id'))
                if not sheet_part:
                    continue
                sheet_rels = _relationships(archive, sheet_part)
                for drawing in ET.fromstring(archive.read(sheet_part)).findall('.//{*}drawing'):
                    drawing_part = sheet_rels.get(drawing.get(REL + 'id'))
                    if not drawing_part:
                        continue
                    drawing_rels = _relationships(archive, drawing_part)
                    drawing_root = ET.fromstring(archive.read(drawing_part))
                    parents = {child: parent for parent in drawing_root.iter() for child in parent}
                    for picture in drawing_root.findall('.//{*}pic'):
                        blip = picture.find('.//' + DRAW + 'blip')
                        media_part = drawing_rels.get(blip.get(REL + 'embed')) if blip is not None else None
                        if media_part is None:
                            continue  # Linked images are not embedded upload data.
                        data = archive.read(media_part)
                        try:
                            with Image.open(BytesIO(data)) as image:
                                width, height = image.size
                                extension = extensions.get(image.format)
                                mimetype = Image.MIME.get(image.format)
                                image.verify()
                        except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError) as exc:
                            result.skipped += 1
                            result.warnings.append(f"Skipped unreadable image on '{sheet.get('name')}': {exc}")
                            continue
                        # Native dimensions and, where supplied, displayed dimensions.
                        extent = picture.find('.//' + DRAW + 'xfrm/' + DRAW + 'ext')
                        if extent is None:
                            anchor = parents.get(picture)
                            while anchor is not None and not anchor.tag.endswith('Anchor'):
                                anchor = parents.get(anchor)
                            if anchor is not None:
                                extent = anchor.find('{*}ext')
                        display_small = False
                        if extent is not None:
                            displayed = [int(extent.get(axis, '0')) / 9525 for axis in ('cx', 'cy')]
                            if all(displayed):
                                display_small = min(displayed) < 64 or displayed[0] * displayed[1] < 10_000
                        if (not extension or not mimetype or min(width, height) < MIN_SIDE
                                or width * height < MIN_AREA or display_small):
                            result.skipped += 1
                            continue
                        result.images.append(EmbeddedImage(data, sheet.get('name', ''), extension, mimetype))
    except Exception as exc:
        raise DocumentImportError(f'Could not read embedded Excel images: {exc}') from exc
    return result
