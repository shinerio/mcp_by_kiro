"""
Stdio Transport Tests

This module contains comprehensive unit tests for the stdio transport implementation.
It verifies the stdio communication mechanism, JSON-RPC message handling, and
error scenarios specific to standard input/output communication.
"""

import pytest
import json
import threading
import time
from unittest.mock import Mock, patch, MagicMock
from io import StringIO
from models.mcp_models import MCPRequest, MCPResponse, MCPError
from transports.stdio_transport import StdioTransport


class TestStdioTransport:
    """Stdio传输实现测试"""
    
    def setup_method(self):
        """测试前设置"""
        self.transport = StdioTransport()
    
    def teardown_method(self):
        """测试后清理"""
        if self.transport.is_running():
            self.transport.stop()
    
    def test_initial_state(self):
        """测试初始状态"""
        assert not self.transport.is_running()
        assert self.transport._input_thread is None
        assert not self.transport._stop_event.is_set()
    
    def test_start_transport(self):
        """测试启动传输层"""
        with patch('sys.stdin'), patch('threading.Thread') as mock_thread:
            mock_thread_instance = Mock()
            mock_thread.return_value = mock_thread_instance
            
            self.transport.start()
            
            assert self.transport.is_running()
            mock_thread.assert_called_once()
            mock_thread_instance.start.assert_called_once()
    
    def test_start_already_running(self):
        """测试重复启动传输层"""
        with patch('sys.stdin'), patch('threading.Thread'):
            self.transport.start()
            assert self.transport.is_running()
            
            # 再次启动应该不做任何操作
            self.transport.start()
            assert self.transport.is_running()
    
    def test_stop_transport(self):
        """测试停止传输层"""
        with patch('sys.stdin'), patch('threading.Thread') as mock_thread:
            mock_thread_instance = Mock()
            mock_thread_instance.is_alive.return_value = True
            mock_thread.return_value = mock_thread_instance
            
            self.transport.start()
            self.transport.stop()
            
            assert not self.transport.is_running()
            assert self.transport._stop_event.is_set()
            mock_thread_instance.join.assert_called_once_with(timeout=1.0)
    
    def test_stop_not_running(self):
        """测试停止未运行的传输层"""
        # 停止未启动的传输层应该不做任何操作
        self.transport.stop()
        assert not self.transport.is_running()
    
    def test_send_response_success(self):
        """测试成功发送响应"""
        with patch('sys.stdout') as mock_stdout:
            mock_stdout.write = Mock()
            mock_stdout.flush = Mock()
            
            # 启动传输层
            with patch('sys.stdin'), patch('threading.Thread'):
                self.transport.start()
            
            response = MCPResponse(
                id="test-123",
                result={"data": "test"}
            )
            
            self.transport.send_response(response)
            
            # 验证输出
            expected_json = response.to_json()
            mock_stdout.write.assert_called_once_with(expected_json + "\n")
            mock_stdout.flush.assert_called_once()
    
    def test_send_response_not_running(self):
        """测试在未运行状态发送响应"""
        response = MCPResponse(id="test", result={})
        
        with pytest.raises(RuntimeError, match="Transport is not running"):
            self.transport.send_response(response)
    
    def test_send_response_error(self):
        """测试发送响应时出错"""
        with patch('sys.stdout') as mock_stdout, patch('sys.stdin'), patch('threading.Thread'):
            mock_stdout.write.side_effect = IOError("Write error")
            
            self.transport.start()
            response = MCPResponse(id="test", result={})
            
            with pytest.raises(RuntimeError, match="Failed to send response"):
                self.transport.send_response(response)
    
    def test_get_connection_info(self):
        """测试获取连接信息"""
        info = self.transport.get_connection_info()
        
        assert info["transport_type"] == "stdio"
        assert info["running"] == self.transport.is_running()
        assert info["input_stream"] == "stdin"
        assert info["output_stream"] == "stdout"
    
    @patch('sys.stdin')
    @patch('sys.stdout')
    def test_input_loop_valid_json(self, mock_stdout, mock_stdin):
        """测试输入循环处理有效JSON"""
        # 模拟标准输入
        test_request = MCPRequest(
            id="test-123",
            method="test_method",
            params={"param": "value"}
        )
        
        mock_stdin.readline.side_effect = [
            test_request.to_json() + "\n",
            ""  # EOF
        ]
        
        # 设置请求处理器
        mock_handler = Mock()
        expected_response = MCPResponse(id="test-123", result={"success": True})
        mock_handler.return_value = expected_response
        
        self.transport.set_request_handler(mock_handler)
        
        # 启动传输层
        self.transport.start()
        
        # 等待输入线程处理
        time.sleep(0.1)
        
        # 验证处理器被调用
        mock_handler.assert_called_once()
        called_request = mock_handler.call_args[0][0]
        assert called_request.id == test_request.id
        assert called_request.method == test_request.method
    
    @patch('sys.stdin')
    @patch('sys.stdout')
    def test_input_loop_invalid_json(self, mock_stdout, mock_stdin):
        """测试输入循环处理无效JSON"""
        # 模拟无效JSON输入
        mock_stdin.readline.side_effect = [
            "invalid json\n",
            ""  # EOF
        ]
        
        mock_stdout.write = Mock()
        mock_stdout.flush = Mock()
        
        self.transport.start()
        time.sleep(0.1)
        
        # 验证发送了错误响应
        mock_stdout.write.assert_called()
        written_data = mock_stdout.write.call_args[0][0]
        
        # 解析写入的响应
        response_json = written_data.strip()
        response_data = json.loads(response_json)
        
        assert "error" in response_data
        assert response_data["error"]["code"] == -32700  # Parse error
    
    @patch('sys.stdin')
    @patch('sys.stdout')
    def test_input_loop_empty_lines(self, mock_stdout, mock_stdin):
        """测试输入循环处理空行"""
        # 模拟包含空行的输入
        mock_stdin.readline.side_effect = [
            "\n",  # 空行
            "   \n",  # 只有空格的行
            ""  # EOF
        ]
        
        mock_stdout.write = Mock()
        
        self.transport.start()
        time.sleep(0.1)
        
        # 空行应该被忽略，不应该有输出
        mock_stdout.write.assert_not_called()
    
    @patch('sys.stdin')
    @patch('sys.stdout')
    def test_input_loop_handler_exception(self, mock_stdout, mock_stdin):
        """测试输入循环中处理器异常"""
        test_request = MCPRequest(
            id="test-123",
            method="error_method",
            params={}
        )
        
        mock_stdin.readline.side_effect = [
            test_request.to_json() + "\n",
            ""  # EOF
        ]
        
        # 设置会抛出异常的处理器
        mock_handler = Mock()
        mock_handler.side_effect = ValueError("Handler error")
        
        self.transport.set_request_handler(mock_handler)
        
        mock_stdout.write = Mock()
        mock_stdout.flush = Mock()
        
        self.transport.start()
        time.sleep(0.1)
        
        # 验证发送了错误响应
        mock_stdout.write.assert_called()
        written_data = mock_stdout.write.call_args[0][0]
        
        response_json = written_data.strip()
        response_data = json.loads(response_json)
        
        assert "error" in response_data
        assert response_data["id"] == "test-123"
    
    @patch('sys.stdin')
    @patch('sys.stdout')
    def test_input_loop_eof_handling(self, mock_stdout, mock_stdin):
        """测试输入循环EOF处理"""
        # 模拟立即EOF
        mock_stdin.readline.return_value = ""
        
        self.transport.start()
        time.sleep(0.1)
        
        # 传输层应该停止运行
        assert not self.transport.is_running()
    
    def test_input_loop_stop_event(self):
        """测试通过停止事件终止输入循环"""
        with patch('sys.stdin') as mock_stdin, patch('sys.stdout'):
            # 模拟阻塞的readline
            mock_stdin.readline.side_effect = lambda: time.sleep(0.1) or "test\n"
            
            self.transport.start()
            assert self.transport.is_running()
            
            # 停止传输层
            self.transport.stop()
            
            # 等待线程结束
            time.sleep(0.2)
            assert not self.transport.is_running()


class TestStdioTransportIntegration:
    """Stdio传输集成测试"""
    
    def setup_method(self):
        """测试前设置"""
        self.transport = StdioTransport()
    
    def teardown_method(self):
        """测试后清理"""
        if self.transport.is_running():
            self.transport.stop()
    
    @patch('sys.stdin')
    @patch('sys.stdout')
    def test_complete_request_response_cycle(self, mock_stdout, mock_stdin):
        """测试完整的请求响应周期"""
        # 准备测试数据
        request = MCPRequest(
            id="integration-test",
            method="base64_encode",
            params={"text": "hello"}
        )
        
        expected_response = MCPResponse(
            id="integration-test",
            result={"encoded": "aGVsbG8="}
        )
        
        # 模拟输入
        mock_stdin.readline.side_effect = [
            request.to_json() + "\n",
            ""  # EOF
        ]
        
        # 设置处理器
        def test_handler(req: MCPRequest) -> MCPResponse:
            if req.method == "base64_encode":
                import base64
                text = req.params.get("text", "")
                encoded = base64.b64encode(text.encode()).decode()
                return MCPResponse(
                    id=req.id,
                    result={"encoded": encoded}
                )
            return MCPResponse(id=req.id, error=MCPError(code=-32601, message="Method not found"))
        
        self.transport.set_request_handler(test_handler)
        
        # 启动并等待处理
        mock_stdout.write = Mock()
        mock_stdout.flush = Mock()
        
        self.transport.start()
        time.sleep(0.1)
        
        # 验证响应
        mock_stdout.write.assert_called()
        written_data = mock_stdout.write.call_args[0][0]
        
        response_json = written_data.strip()
        response_data = json.loads(response_json)
        
        assert response_data["id"] == "integration-test"
        assert response_data["result"]["encoded"] == "aGVsbG8="
    
    @patch('sys.stdin')
    @patch('sys.stdout')
    def test_multiple_requests_sequence(self, mock_stdout, mock_stdin):
        """测试多个请求的顺序处理"""
        # 准备多个请求
        requests = [
            MCPRequest(id=f"req-{i}", method="test", params={"value": i})
            for i in range(3)
        ]
        
        # 模拟输入序列
        input_lines = [req.to_json() + "\n" for req in requests] + [""]
        mock_stdin.readline.side_effect = input_lines
        
        # 设置计数处理器
        call_count = 0
        
        def counting_handler(req: MCPRequest) -> MCPResponse:
            nonlocal call_count
            call_count += 1
            return MCPResponse(
                id=req.id,
                result={"call_number": call_count, "value": req.params.get("value")}
            )
        
        self.transport.set_request_handler(counting_handler)
        
        # 收集所有输出
        written_responses = []
        
        def capture_write(data):
            written_responses.append(data.strip())
        
        mock_stdout.write.side_effect = capture_write
        mock_stdout.flush = Mock()
        
        self.transport.start()
        time.sleep(0.2)  # 等待所有请求处理完成
        
        # 验证所有响应
        assert len(written_responses) == 3
        
        for i, response_json in enumerate(written_responses):
            response_data = json.loads(response_json)
            assert response_data["id"] == f"req-{i}"
            assert response_data["result"]["call_number"] == i + 1
            assert response_data["result"]["value"] == i
    
    @patch('sys.stdin')
    @patch('sys.stdout')
    def test_error_handling_and_recovery(self, mock_stdout, mock_stdin):
        """测试错误处理和恢复能力"""
        # 准备混合的有效和无效请求
        valid_request = MCPRequest(id="valid", method="test", params={})
        
        input_sequence = [
            "invalid json\n",  # 无效JSON
            valid_request.to_json() + "\n",  # 有效请求
            ""  # EOF
        ]
        
        mock_stdin.readline.side_effect = input_sequence
        
        # 设置处理器
        def test_handler(req: MCPRequest) -> MCPResponse:
            return MCPResponse(id=req.id, result={"processed": True})
        
        self.transport.set_request_handler(test_handler)
        
        # 收集输出
        written_responses = []
        
        def capture_write(data):
            written_responses.append(data.strip())
        
        mock_stdout.write.side_effect = capture_write
        mock_stdout.flush = Mock()
        
        self.transport.start()
        time.sleep(0.2)
        
        # 验证输出：应该有错误响应和成功响应
        assert len(written_responses) == 2
        
        # 第一个响应应该是解析错误
        error_response = json.loads(written_responses[0])
        assert "error" in error_response
        assert error_response["error"]["code"] == -32700
        
        # 第二个响应应该是成功处理
        success_response = json.loads(written_responses[1])
        assert success_response["id"] == "valid"
        assert success_response["result"]["processed"] is True


class TestStdioTransportEdgeCases:
    """Stdio传输边界情况测试"""
    
    def setup_method(self):
        """测试前设置"""
        self.transport = StdioTransport()
    
    def teardown_method(self):
        """测试后清理"""
        if self.transport.is_running():
            self.transport.stop()
    
    @patch('sys.stdin')
    @patch('sys.stdout')
    def test_large_message_handling(self, mock_stdout, mock_stdin):
        """测试大消息处理"""
        # 创建大参数的请求
        large_text = "x" * 10000  # 10KB文本
        large_request = MCPRequest(
            id="large-test",
            method="test",
            params={"large_data": large_text}
        )
        
        mock_stdin.readline.side_effect = [
            large_request.to_json() + "\n",
            ""
        ]
        
        # 设置处理器
        def large_handler(req: MCPRequest) -> MCPResponse:
            data_size = len(req.params.get("large_data", ""))
            return MCPResponse(
                id=req.id,
                result={"data_size": data_size}
            )
        
        self.transport.set_request_handler(large_handler)
        
        mock_stdout.write = Mock()
        mock_stdout.flush = Mock()
        
        self.transport.start()
        time.sleep(0.1)
        
        # 验证大消息被正确处理
        mock_stdout.write.assert_called()
        written_data = mock_stdout.write.call_args[0][0]
        
        response_data = json.loads(written_data.strip())
        assert response_data["result"]["data_size"] == 10000
    
    @patch('sys.stdin')
    @patch('sys.stdout')
    def test_unicode_message_handling(self, mock_stdout, mock_stdin):
        """测试Unicode消息处理"""
        # 包含Unicode字符的请求
        unicode_request = MCPRequest(
            id="unicode-test",
            method="test",
            params={"text": "你好世界 🌍 émojis"}
        )
        
        mock_stdin.readline.side_effect = [
            unicode_request.to_json() + "\n",
            ""
        ]
        
        def unicode_handler(req: MCPRequest) -> MCPResponse:
            text = req.params.get("text", "")
            return MCPResponse(
                id=req.id,
                result={"received_text": text, "length": len(text)}
            )
        
        self.transport.set_request_handler(unicode_handler)
        
        mock_stdout.write = Mock()
        mock_stdout.flush = Mock()
        
        self.transport.start()
        time.sleep(0.1)
        
        # 验证Unicode字符被正确处理
        mock_stdout.write.assert_called()
        written_data = mock_stdout.write.call_args[0][0]
        
        response_data = json.loads(written_data.strip())
        assert response_data["result"]["received_text"] == "你好世界 🌍 émojis"
    
    def test_thread_safety(self):
        """测试线程安全性"""
        with patch('sys.stdin'), patch('sys.stdout'):
            # 多次启动和停止应该是安全的
            for _ in range(3):
                self.transport.start()
                assert self.transport.is_running()
                
                self.transport.stop()
                assert not self.transport.is_running()
    
    @patch('sys.stdin')
    @patch('sys.stdout')
    def test_input_loop_exception_handling(self, mock_stdout, mock_stdin):
        """测试输入循环异常处理"""
        # 模拟readline抛出异常后返回EOF
        mock_stdin.readline.side_effect = [IOError("Input error"), ""]
        
        # 启动传输层
        self.transport.start()
        time.sleep(0.2)  # 给更多时间处理异常
        
        # 传输层应该优雅地处理异常并停止
        # 由于异常处理，最终会停止运行
        assert not self.transport.is_running()


if __name__ == "__main__":
    pytest.main([__file__])