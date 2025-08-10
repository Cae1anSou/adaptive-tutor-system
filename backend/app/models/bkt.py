"""
BKT (Bayesian Knowledge Tracing) 模型实现

BKT模型是一种用于追踪学习者知识点掌握情况的概率模型。
它基于隐马尔可夫模型，有四个核心参数：
- p_init: 初始掌握概率
- p_transit: 学习转移概率（未掌握->掌握）
- p_slip: 失误概率（掌握但答错）
- p_guess: 猜测概率（未掌握但答对）

模型状态：
- L(t): 在第t次尝试前，学习者掌握知识点的概率
- 通过观测学习者的答题结果（正确/错误），模型会更新对学习者掌握情况的估计
"""

from typing import Dict, Any


class BKTModel:
    # 默认参数，可以根据实际数据进行调整
    DEFAULT_PARAMS = {
        'p_init': 0.2,     # 初始掌握概率
        'p_transit': 0.15, # 学习转移概率
        'p_slip': 0.1,     # 失误概率
        'p_guess': 0.2     # 猜测概率
    }

    def __init__(self, params: Dict[str, float] = None):
        """
        初始化BKT模型
        
        Args:
            params: 模型参数字典，包含p_init, p_transit, p_slip, p_guess
        """
        if params is None:
            params = self.DEFAULT_PARAMS
            
        # 确保所有必需参数都存在
        self.p_init = params.get('p_init', self.DEFAULT_PARAMS['p_init'])
        self.p_transit = params.get('p_transit', self.DEFAULT_PARAMS['p_transit'])
        self.p_slip = params.get('p_slip', self.DEFAULT_PARAMS['p_slip'])
        self.p_guess = params.get('p_guess', self.DEFAULT_PARAMS['p_guess'])
        
        # 初始化知识点掌握概率
        self.mastery_prob = self.p_init

    def update(self, is_correct: bool) -> float:
        """
        根据答题结果更新知识点掌握概率
        
        Args:
            is_correct: 答题是否正确
            
        Returns:
            更新后的知识点掌握概率
        """
        # 计算观测概率
        if is_correct:
            # 答对的概率 = 掌握且未失误 + 未掌握但猜对
            p_obs = self.mastery_prob * (1 - self.p_slip) + (1 - self.mastery_prob) * self.p_guess
        else:
            # 答错的概率 = 掌握但失误 + 未掌握且未猜对
            p_obs = self.mastery_prob * self.p_slip + (1 - self.mastery_prob) * (1 - self.p_guess)
            
        # 避免除零错误
        if p_obs == 0:
            p_obs = 1e-10

        # 贝叶斯更新：根据观测结果更新掌握概率
        if is_correct:
            # P(掌握 | 答对) = P(答对 | 掌握) * P(掌握) / P(答对)
            posterior_mastery = (self.mastery_prob * (1 - self.p_slip)) / p_obs
        else:
            # P(掌握 | 答错) = P(答错 | 掌握) * P(掌握) / P(答错)
            posterior_mastery = (self.mastery_prob * self.p_slip) / p_obs
            
        # 应用学习转移：学习者可能通过这次练习学到了知识
        # 新的掌握概率 = 后验概率 + (1-后验概率) * 学习转移概率
        self.mastery_prob = posterior_mastery + (1 - posterior_mastery) * self.p_transit
            
        # 确保概率在有效范围内
        self.mastery_prob = max(0.0, min(1.0, self.mastery_prob))
        
        return self.mastery_prob

    def get_mastery_prob(self) -> float:
        """
        获取当前知识点掌握概率
        
        Returns:
            知识点掌握概率
        """
        return self.mastery_prob

    def to_dict(self) -> Dict[str, Any]:
        """
        将模型序列化为字典，用于存储
        
        Returns:
            包含模型参数和状态的字典
        """
        return {
            'p_init': self.p_init,
            'p_transit': self.p_transit,
            'p_slip': self.p_slip,
            'p_guess': self.p_guess,
            'mastery_prob': self.mastery_prob
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BKTModel':
        """
        从字典反序列化创建BKT模型
        
        Args:
            data: 包含模型参数的字典
            
        Returns:
            BKTModel实例
        """
        # 提取参数
        params = {
            'p_init': data.get('p_init', cls.DEFAULT_PARAMS['p_init']),
            'p_transit': data.get('p_transit', cls.DEFAULT_PARAMS['p_transit']),
            'p_slip': data.get('p_slip', cls.DEFAULT_PARAMS['p_slip']),
            'p_guess': data.get('p_guess', cls.DEFAULT_PARAMS['p_guess'])
        }
        
        # 创建模型实例
        model = cls(params)
        
        # 恢复状态
        model.mastery_prob = data.get('mastery_prob', params['p_init'])
        
        return model

    def __str__(self) -> str:
        """
        返回模型的字符串表示
        """
        return f"BKTModel(mastery_prob={self.mastery_prob:.3f})"