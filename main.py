from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import declarative_base, sessionmaker
import os
import shutil
import cloudinary
import cloudinary.uploader
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

app = FastAPI()

# ==================== 配置 Cloudinary ====================
# 注意：这里加了 .strip() 去掉所有隐藏空格，并强制使用 sha256 防止签名报错
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME", "").strip(),
    api_key=os.getenv("CLOUDINARY_API_KEY", "").strip(),
    api_secret=os.getenv("CLOUDINARY_API_SECRET", "").strip(),
    signature_algorithm='sha256'  # 解决 Invalid Signature
)

# 打印一下检查（启动时在终端会显示）
print("☁️ 正在使用的 Cloud Name:", os.getenv("CLOUDINARY_CLOUD_NAME", "").strip())

# ==================== 数据库配置 ====================
SQLALCHEMY_DATABASE_URL = "sqlite:///./photos.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Photo(Base):
    __tablename__ = "photos"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    url = Column(String) 

Base.metadata.create_all(bind=engine)

# ==================== 前端页面与静态文件 ====================
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

@app.get("/")
def read_index():
    return FileResponse("index.html")

# ==================== 获取照片列表 ====================
@app.get("/api/photos")
def get_photos():
    db = SessionLocal()
    photos = db.query(Photo).all()
    db.close()
    data = [{"id": p.id, "title": p.title, "url": p.url} for p in photos]
    return {"status": "success", "data": data}

# ==================== 上传照片 ====================
@app.post("/api/upload")
async def upload_photo(
    file: UploadFile = File(...),
    title: str = Form(...),
    password: str = Form(...)
):
    if password != "woaini":
        raise HTTPException(status_code=403, detail="暗号不对，不能传照片哦！")

    # 上传到 Cloudinary
    try:
        upload_result = cloudinary.uploader.upload(file.file)
        image_url = upload_result.get("secure_url")
    except Exception as e:
        # 如果还是报错，这里会把具体的错误信息返回给网页
        raise HTTPException(status_code=500, detail=f"图片上传失败: {str(e)}")

    # 存入数据库
    db = SessionLocal()
    new_photo = Photo(title=title, url=image_url)
    db.add(new_photo)
    db.commit()
    db.refresh(new_photo)
    db.close()
    return {"status": "success", "message": "照片已永久保存！"}

# ==================== 删除照片 ====================
@app.delete("/api/photos/{photo_id}")
def delete_photo(photo_id: int, password: str):
    if password != "woaini":
        raise HTTPException(status_code=403, detail="暗号不对，不能删除哦！")
    db = SessionLocal()
    photo = db.query(Photo).filter(Photo.id == photo_id).first()
    if not photo:
        db.close()
        raise HTTPException(status_code=404, detail="照片不存在")
    
    db.delete(photo)
    db.commit()
    db.close()
    return {"status": "success", "message": "照片已删除"}