import os
import sys
import logging
from pathlib import Path
from typing import Optional
import requests
from transformers import AutoTokenizer, AutoModelForSequenceClassification

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def check_internet_connection() -> bool:
    """检查网络连接是否正常"""
    try:
        requests.get("https://huggingface.co/", timeout=10)
        return True
    except requests.RequestException:
        return False

def download_model(model_repo: str, save_directory: str) -> bool:
    """
    下载并保存模型
    
    Args:
        model_repo: 模型仓库ID
        save_directory: 保存目录
        
    Returns:
        bool: 是否下载并保存成功
    """
    try:
        # 检查网络连接
        if not check_internet_connection():
            logger.error("网络连接失败，请检查网络设置")
            return False
            
        # 检查保存目录是否可写
        save_path = Path(save_directory)
        try:
            save_path.mkdir(parents=True, exist_ok=True)
            test_file = save_path / ".write_test"
            test_file.touch()
            test_file.unlink()
        except (IOError, OSError) as e:
            logger.error(f"无法写入保存目录 {save_path.absolute()}: {str(e)}")
            return False
            
        logger.info(f"正在从 {model_repo} 下载模型...")
        
        try:
            # 下载tokenizer和模型
            tokenizer = AutoTokenizer.from_pretrained(model_repo)
            model = AutoModelForSequenceClassification.from_pretrained(model_repo)
        except Exception as e:
            logger.error(f"模型下载失败: {str(e)}")
            return False
            
        try:
            logger.info(f"正在保存模型到 {save_path.absolute()}...")
            tokenizer.save_pretrained(save_directory)
            model.save_pretrained(save_directory)
            logger.info("模型下载并保存完成！")
            return True
            
        except Exception as e:
            logger.error(f"模型保存失败: {str(e)}")
            # 清理可能已保存的部分文件
            if save_path.exists():
                import shutil
                shutil.rmtree(save_path, ignore_errors=True)
            return False
            
    except Exception as e:
        logger.error(f"发生未预期的错误: {str(e)}", exc_info=True)
        return False

def main():
    # 配置参数
    MODEL_REPO = "wxt5981/bert-base-uncased"
    SAVE_DIRECTORY = "models/sentiment_bert"
    
    success = download_model(MODEL_REPO, SAVE_DIRECTORY)
    if not success:
        logger.error("模型下载或保存失败！")
        sys.exit(1)

if __name__ == "__main__":
    main()