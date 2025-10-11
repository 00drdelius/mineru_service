import enum
from typing import *
from pydantic import BaseModel

class BlockType(enum.Enum):
    TEXT = "text"  # 文本
    TITLE = "title"  # 段落标题
    TABLE = "table"  # 表格
    IMAGE = "image"  # 图像
    CODE = "code"  # 代码
    ALGORITHM = "algorithm"  # 算法/伪代码
    HEADER = "header"  # 页眉
    FOOTER = "footer"  # 页脚
    PAGE_NUMBER = "page_number"  # 页码
    PAGE_FOOTNOTE = "page_footnote"  # 脚注
    ASIDE_TEXT = "aside_text"  # 侧栏文本(装订线等)
    EQUATION = "equation"  # 公式(独立公式)
    EQUATION_BLOCK = "equation_block"  # 公式块(多行公式)
    REF_TEXT = "ref_text"  # 参考文献(一条)
    LIST = "list"  # 列表块(无序/有序列表)
    PHONETIC = "phonetic"  # 注音符号

    # captions
    TABLE_CAPTION = "table_caption"  # 表格标题
    IMAGE_CAPTION = "image_caption"  # 图像标题
    CODE_CAPTION = "code_caption"  # 代码标题
    TABLE_FOOTNOTE = "table_footnote"  # 表格脚注
    IMAGE_FOOTNOTE = "image_footnote"  # 图像脚注

    UNKNOWN = "unknown"  # 未知块


class ExtractedBlock(BaseModel):
    type: BlockType
    bbox: Tuple[float, float, float, float] | None = None
    angle: int | None = None
    content: str | None = None

class ExtractionResponse(BaseModel):
    list_of_extracted_blocks: List[List[ExtractedBlock]]