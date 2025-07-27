"""
Base64 Service Interface

This module defines the interface for Base64 encoding and decoding operations.
The service provides core business logic for text-to-base64 and base64-to-text
conversions with proper validation and error handling.
"""

import base64
import re
from abc import ABC, abstractmethod
from typing import Tuple


class Base64ServiceInterface(ABC):
    """
    Base64服务抽象接口
    
    定义Base64编码解码服务的标准接口。实现类必须提供编码、解码和验证功能。
    这个接口确保了不同实现之间的一致性，便于测试和扩展。
    """
    
    @abstractmethod
    def encode(self, text: str) -> str:
        """
        将文本字符串编码为base64格式
        
        Args:
            text: 需要编码的文本字符串
            
        Returns:
            str: 编码后的base64字符串
            
        Raises:
            ValueError: 当输入文本无效时抛出
        """
        pass
    
    @abstractmethod
    def decode(self, base64_string: str) -> str:
        """
        将base64字符串解码为文本
        
        Args:
            base64_string: 需要解码的base64字符串
            
        Returns:
            str: 解码后的文本字符串
            
        Raises:
            ValueError: 当base64字符串格式无效时抛出
        """
        pass
    
    @abstractmethod
    def validate_base64(self, base64_string: str) -> Tuple[bool, str]:
        """
        验证base64字符串的格式正确性
        
        Args:
            base64_string: 需要验证的base64字符串
            
        Returns:
            Tuple[bool, str]: (是否有效, 错误信息或空字符串)
        """
        pass
    
    @abstractmethod
    def is_valid_text(self, text: str) -> Tuple[bool, str]:
        """
        验证文本字符串是否适合编码
        
        Args:
            text: 需要验证的文本字符串
            
        Returns:
            Tuple[bool, str]: (是否有效, 错误信息或空字符串)
        """
        pass


class Base64Service(Base64ServiceInterface):
    """
    Base64服务实现类
    
    提供Base64编码解码的具体实现，包含完整的验证和错误处理功能。
    支持UTF-8文本的编码解码，并提供详细的错误信息。
    """
    
    # Base64字符集正则表达式 - 只允许A-Z, a-z, 0-9, +, /, = 字符
    BASE64_PATTERN = re.compile(r'^[A-Za-z0-9+/]*={0,2}$')
    
    # 最大文本长度限制 (1MB)
    MAX_TEXT_LENGTH = 1024 * 1024
    
    def encode(self, text: str) -> str:
        """
        将文本字符串编码为base64格式
        
        使用UTF-8编码将文本转换为字节，然后进行base64编码。
        包含输入验证以确保文本的有效性。
        
        Args:
            text: 需要编码的文本字符串
            
        Returns:
            str: 编码后的base64字符串
            
        Raises:
            ValueError: 当输入文本无效时抛出
        """
        # 验证输入文本
        is_valid, error_msg = self.is_valid_text(text)
        if not is_valid:
            raise ValueError(f"Invalid text input: {error_msg}")
        
        try:
            # 将文本转换为UTF-8字节
            text_bytes = text.encode('utf-8')
            
            # 进行base64编码
            encoded_bytes = base64.b64encode(text_bytes)
            
            # 转换为字符串并返回
            return encoded_bytes.decode('ascii')
            
        except UnicodeEncodeError as e:
            raise ValueError(f"Text encoding failed: {str(e)}")
        except Exception as e:
            raise ValueError(f"Base64 encoding failed: {str(e)}")
    
    def decode(self, base64_string: str) -> str:
        """
        将base64字符串解码为文本
        
        验证base64格式后进行解码，并将结果转换为UTF-8文本。
        提供详细的错误信息以便调试。
        
        Args:
            base64_string: 需要解码的base64字符串
            
        Returns:
            str: 解码后的文本字符串
            
        Raises:
            ValueError: 当base64字符串格式无效时抛出
        """
        # 验证base64格式
        is_valid, error_msg = self.validate_base64(base64_string)
        if not is_valid:
            raise ValueError(f"Invalid base64 input: {error_msg}")
        
        try:
            # 进行base64解码
            decoded_bytes = base64.b64decode(base64_string)
            
            # 转换为UTF-8文本
            return decoded_bytes.decode('utf-8')
            
        except base64.binascii.Error as e:
            raise ValueError(f"Base64 decoding failed: Invalid base64 format - {str(e)}")
        except UnicodeDecodeError as e:
            raise ValueError(f"Text decoding failed: Invalid UTF-8 sequence - {str(e)}")
        except Exception as e:
            raise ValueError(f"Base64 decoding failed: {str(e)}")
    
    def validate_base64(self, base64_string: str) -> Tuple[bool, str]:
        """
        验证base64字符串的格式正确性
        
        检查字符串是否符合base64格式要求：
        1. 只包含有效的base64字符 (A-Z, a-z, 0-9, +, /, =)
        2. 长度必须是4的倍数（考虑填充）
        3. 填充字符'='只能出现在末尾，最多2个
        
        Args:
            base64_string: 需要验证的base64字符串
            
        Returns:
            Tuple[bool, str]: (是否有效, 错误信息或空字符串)
        """
        if not isinstance(base64_string, str):
            return False, "Input must be a string"
        
        # 检查空字符串
        if not base64_string:
            return False, "Base64 string cannot be empty"
        
        # 检查长度是否为4的倍数
        if len(base64_string) % 4 != 0:
            return False, f"Base64 string length must be multiple of 4, got {len(base64_string)}"
        
        # 检查字符集是否有效
        if not self.BASE64_PATTERN.match(base64_string):
            return False, "Base64 string contains invalid characters"
        
        # 检查填充字符的位置
        padding_count = base64_string.count('=')
        if padding_count > 2:
            return False, "Base64 string has too many padding characters"
        
        if padding_count > 0:
            # 填充字符必须在末尾
            if not base64_string.endswith('=' * padding_count):
                return False, "Padding characters must be at the end"
            
            # 检查填充前的字符不能是填充字符
            non_padding_part = base64_string[:-padding_count]
            if '=' in non_padding_part:
                return False, "Padding characters can only appear at the end"
        
        # 尝试实际解码以验证格式
        try:
            base64.b64decode(base64_string, validate=True)
        except Exception:
            return False, "Base64 string format is invalid"
        
        return True, ""
    
    def is_valid_text(self, text: str) -> Tuple[bool, str]:
        """
        验证文本字符串是否适合编码
        
        检查文本的基本有效性：
        1. 必须是字符串类型
        2. 长度不能超过限制
        3. 必须是有效的UTF-8文本
        
        Args:
            text: 需要验证的文本字符串
            
        Returns:
            Tuple[bool, str]: (是否有效, 错误信息或空字符串)
        """
        if not isinstance(text, str):
            return False, "Input must be a string"
        
        # 允许空字符串
        if len(text) == 0:
            return True, ""
        
        # 检查长度限制
        if len(text) > self.MAX_TEXT_LENGTH:
            return False, f"Text too long: {len(text)} characters (max: {self.MAX_TEXT_LENGTH})"
        
        # 验证UTF-8编码
        try:
            text.encode('utf-8')
        except UnicodeEncodeError as e:
            return False, f"Invalid UTF-8 text: {str(e)}"
        
        return True, ""