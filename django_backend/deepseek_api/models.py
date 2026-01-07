from django.db import models
from django.db.models import F
import string
import random
import time
import logging
logger = logging.getLogger(__name__)

from django.db.models import indexes

class APIKey(models.Model):
    key = models.CharField(max_length=32, unique=True)
    user = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    expiry_time = models.IntegerField()  # 过期时间戳
    
    @classmethod
    def generate_key(cls, length=32):
        """生成随机 API Key"""
        characters = string.ascii_letters + string.digits
        return ''.join(random.choice(characters) for _ in range(length))
    
    def is_valid(self):
        """检查 API Key 是否未过期"""
        return time.time() < self.expiry_time
    
    def __str__(self):
        return f"{self.user} - {self.key}"


class RateLimit(models.Model):
    api_key = models.ForeignKey(APIKey, on_delete=models.CASCADE,
                                db_index=True, to_field='key', related_name='rate_limits')
    count = models.IntegerField(default=0)
    reset_time = models.IntegerField()  # 重置时间戳

    class Meta:
        indexes = [
            models.Index(fields=['api_key', 'reset_time'])
        ]
    
    def should_limit(self, max_requests, interval):
        """检查是否应该限制请求"""
        current_time = time.time()
        if current_time > self.reset_time:
            self.count = 0
            self.reset_time = current_time + interval
            self.save()
            return False
        return self.count >= max_requests


class ConversationSession(models.Model):
    session_id = models.CharField(max_length=100)
    # 正确的外键定义：关联 APIKey 的 id（默认）
    user = models.ForeignKey(
        APIKey, 
        on_delete=models.CASCADE, 
        related_name='sessions'
    )
    context = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('session_id', 'user')  # 确保用户+会话ID唯一
    
    def update_context(self, user_input, bot_reply):
        """原子更新上下文，避免并发覆盖"""
        new_entry = f"用户：{user_input}\n回复：{bot_reply}\n"
        
        print(f"\n💾 [模型层] ConversationSession.update_context() 被调用")
        print(f"💾 [会话信息] ID: {self.pk}, session_id: '{self.session_id}', user: '{self.user.user}'")
        print(f"💾 [更新前长度] {len(self.context)} 字符")
        print(f"💾 [新增条目] {new_entry.strip()}")
        
        # 数据库层面拼接，而非内存中
        ConversationSession.objects.filter(
            pk=self.pk,  # 精确匹配当前会话
            user=self.user  # 确保用户一致
        ).update(context=F('context') + new_entry)
        
        # 刷新实例，获取更新后的值
        old_length = len(self.context)
        self.refresh_from_db()
        new_length = len(self.context)
        
        print(f"💾 [数据库更新] 原子操作完成")
        print(f"💾 [更新后长度] {old_length} → {new_length} 字符")
        print(f"💾 [实例刷新] 从数据库重新加载最新数据")

        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"更新会话 {self.session_id}（用户：{self.user.user}）：{new_entry}")
    
    def clear_context(self):
        """清空对话上下文"""
        print(f"\n🗑️ [模型层] ConversationSession.clear_context() 被调用")
        print(f"🗑️ [会话信息] ID: {self.pk}, session_id: '{self.session_id}', user: '{self.user.user}'")
        print(f"🗑️ [清空前长度] {len(self.context)} 字符")
        
        self.context = ""
        self.save()
        
        print(f"🗑️ [清空完成] 上下文已清空并保存到数据库")
        print(f"🗑️ [清空后长度] {len(self.context)} 字符")
    
    def __str__(self):
        return self.session_id
