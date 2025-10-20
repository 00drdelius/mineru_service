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

    def renderer(self,string:str|None):
        if string==None:
            return ""
        string = string.replace("\\(","$").replace("\\)","$") #NOTE replace oneline latex
        string = string.replace("\\[","$$\n").replace("\\]","\n$$") #NOTE equation, equation_block
        match self.value:
            case "title" | "header":
                string = "# "+string
            case "algorithm":
                string="```\n"+string+"\n```"
            case "page_footnote":
                string="> "+string
        return string

class OutputFormats(enum.Enum):
    JSON = "json"
    MARKDOWN = "markdown"

class ContentBlock(BaseModel):
    type: BlockType
    bbox: Tuple[float, float, float, float] | None = None
    angle: int | None = None
    content: str | None = None

class OnePageResult(BaseModel):
    content_blocks: List[ContentBlock] | None = None
    "list of content blocks in one page."
    markdown_content: str | None = None
    "result converted to markdown"

class PageResults(BaseModel):
    """multi page results"""
    list_of_extracted_pages: List[OnePageResult]
    "list of page results. Each element contains one page of OCR blocks."


if __name__ == '__main__':
    import json
    txts=[]
    with open("response.json","r",encoding='utf8') as f:
        data=json.load(f)
        data=PageResults.model_validate(data)
        for item in data.list_of_extracted_pages:
            test_item = item.content_blocks[0]
            content = test_item.type.renderer(test_item.content)
            txts.append(content)

    with open("response.md","w",encoding='utf8') as f:
        f.write("\n".join(txts))
