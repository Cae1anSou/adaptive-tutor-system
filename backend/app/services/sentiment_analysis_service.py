import os
import warnings
import logging
from app.schemas.chat import SentimentAnalysisResult

# 配置日志记录器
logger = logging.getLogger(__name__)

class SentimentAnalysisService:
    def __init__(self):
        self.model_available = False
        self.model = None
        self.tokenizer = None
        self.device = None
        
        # 检查模型文件是否存在
        model_dir = 'models/sentiment_bert'
        if os.path.exists(model_dir):
            try:
                self._load_model_with_fallback(model_dir)
            except Exception as e:
                logger.warning(f"BERT模型加载失败: {e}")
                logger.info("将使用简化的情感分析功能")
                self.model_available = False
        else:
            logger.warning("未找到BERT模型文件，跳过模型加载")
            logger.info("情感分析功能将返回中性结果")
            self.model_available = False
        
        # 标签映射
        self.label_map = {0: 'NEGATIVE', 1: 'NEUTRAL', 2: 'POSITIVE'}
    
    def _load_model_with_fallback(self, model_dir: str):
        """
        尝试加载模型，先尝试BertForSequenceClassification，失败则尝试DistilBertForSequenceClassification
        """
        # 只在模型文件存在时才导入相关库
        import torch
        from transformers import BertTokenizer, BertForSequenceClassification
        from transformers.utils import logging as transformers_logging
        
        # 设置日志级别和警告
        os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
        os.environ["PYTHONWARNINGS"] = "ignore"
        warnings.filterwarnings("ignore")
        transformers_logging.set_verbosity_error()
        
        # 尝试加载BERT模型
        try:
            # 加载tokenizer
            self.tokenizer = BertTokenizer.from_pretrained(model_dir)
            
            # 加载BertForSequenceClassification模型
            self.model = BertForSequenceClassification.from_pretrained(
                model_dir,
                local_files_only=True
            )
            logger.info("BERT情感分析模型加载成功")
        except Exception as e1:
            logger.warning(f"BERT模型加载失败: {e1}")
            # 如果BERT模型加载失败，尝试加载DistilBERT模型
            try:
                from transformers import DistilBertTokenizer, DistilBertForSequenceClassification
                
                # 加载DistilBERT tokenizer
                self.tokenizer = DistilBertTokenizer.from_pretrained(model_dir)
                
                # 加载DistilBertForSequenceClassification模型
                self.model = DistilBertForSequenceClassification.from_pretrained(
                    model_dir,
                    local_files_only=True
                )
                logger.info("DistilBERT情感分析模型加载成功")
            except Exception as e2:
                logger.error(f"DistilBERT模型加载失败: {e2}")
                raise e2  # 如果两种模型都加载失败，抛出异常
        
        # 设置设备
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.model = self.model.to(self.device)
        self.model.eval()
        self.model_available = True
      
    def analyze_sentiment(self, text: str) -> SentimentAnalysisResult:
        """
        Analyzes the sentiment of a given text.
        Returns a SentimentAnalysisResult object
        """
        if not text.strip():
            return SentimentAnalysisResult(
                label="NEUTRAL",
                confidence=1.0
            )
        
        # 如果模型不可用，返回中性结果
        if not self.model_available:
            return SentimentAnalysisResult(
                label="NEUTRAL",
                confidence=1.0
            )
        
        # 只在模型可用时才导入torch
        import torch
        
        # 对输入文本进行编码
        encoding = self.tokenizer.encode_plus(
            text,
            add_special_tokens=True,
            max_length=128,
            truncation=True,
            padding='max_length',
            return_attention_mask=True,
            return_tensors='pt'
        )
        
        # 将输入数据移动到指定设备
        input_ids = encoding['input_ids'].to(self.device)
        attention_mask = encoding['attention_mask'].to(self.device)
        
        # 模型推理
        with torch.no_grad():
            outputs = self.model(input_ids, attention_mask=attention_mask)
            logits = outputs.logits
            probs = torch.nn.functional.softmax(logits, dim=1)
            score, pred = torch.max(probs, dim=1)
            
        # 返回结果
        logger.info(f"Sentiment analysis result: {self.label_map.get(pred.item(), 'NEUTRAL')} ({score.item()})")
        return SentimentAnalysisResult(
            label=self.label_map.get(pred.item(), 'NEUTRAL'),
            confidence=score.item()
        )

# 创建单例实例
sentiment_analysis_service = SentimentAnalysisService()

if __name__ == "__main__":
    sentiment_analysis_service = SentimentAnalysisService()
    while True:
        input_text = input("Enter your text: ")
        if input_text.lower() == "exit":
            break
        print(sentiment_analysis_service.analyze_sentiment(input_text))