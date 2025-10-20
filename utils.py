import asyncio
from typing import *
from io import BytesIO

import fitz
from fitz import Pixmap
from PIL import Image

allowed_content_types=[
    "application/pdf",
    "image/jpeg",
    "image/png",
]
allowed_file_formats=["pdf","jpg","jpeg","png"]

def check_mimetype(content_type:str=None, filename:str=None)->Literal["pdf","image"]:
    print("content_type: ",content_type,"; ","filename: ",filename)
    if filename:
        extension=filename.rsplit(".",1)[-1] 
        assert extension in allowed_file_formats, "unsupported file format: %s" % filename
        if extension=='pdf':
            return "pdf"
        else:
            return "image"
    if content_type:
        assert content_type in allowed_content_types, "unsupported content type: %s" % content_type
        if content_type=='application/pdf':
            return "pdf"
        else:
            return "image"

T = TypeVar('T')

async def sync_to_async(obj: Callable[..., T], *args: Any, **kwargs: Any) -> T:
    "convert sync function to async"
    try:
        result = await asyncio.to_thread(obj, *args, **kwargs)
    except Exception as exc:
        raise type(exc)(f"Error in sync_to_async: {exc}") from exc
    else:
        return result


def pdf_bytes_to_images(pdf_bytes:bytes, dpi=300)->list[Image.Image]:
    """
    convert pdf from stream to jpeg image in BytesIO
    
    Args:
        pdf_bytes(bytes): pdf stream
        dpi(int): image resolution
    
    Returns:
        out(list[BytesIO]): list of jpeg image in BytesIO
    """
    # 从字节数据打开 PDF
    pdf_document = fitz.open(stream=pdf_bytes, filetype="pdf")
    images_list = []
    
    zoom = dpi / 72
    mat = fitz.Matrix(zoom, zoom)
    
    for page_num in range(len(pdf_document)):
        page = pdf_document[page_num]
        pix:Pixmap = page.get_pixmap(matrix=mat)
        
        images_list.append(pix.pil_image())

    pdf_document.close()
    return images_list


async def convert_to_images(
    file_bytes:bytes, file_type:str, dpi:int=300
)->list[Image.Image]:
    """
    convert file bytes into list of `PIL.Image`.
    Args:
        file_bytes(bytes): file bytes
        file_type(str): file type
        dpi(int): image resolution
    Returns:
        out(list[PIL.Image]): list of `PIL.Image`
    """
    def stream_to_pil_image(file_bytes:bytes)->list[Image.Image]:
        with BytesIO(file_bytes) as buf:
            img = Image.open(buf)
            img.load() #NOTE 强制加载图像数据
            return [img]

    if file_type=='pdf':
        #NOTE only needs to set await among the whole pdf_bytes_to_images function
        result = await sync_to_async(pdf_bytes_to_images,file_bytes,dpi=dpi)
        return result
    elif file_type=='image':
        result = await sync_to_async(stream_to_pil_image, file_bytes)
        return result
    
if __name__ == '__main__':
    with open("test/《职工非因工伤残或因病丧失劳动能力程度鉴定标准(试行)》.pdf",'rb') as f:
    # with open("test/images/0.jpg",'rb') as f:
        result = asyncio.run(convert_to_images(f.read(),file_type="pdf"))
    for idx,item in enumerate(result):
        # item.save(f"test.jpg",format="jpeg")
        item.save(f"test/{idx}.jpg",format='jpeg')
