"""
Transport Layer Interface Tests

This module contains unit tests for the transport layer abstract interface
and base implementation. It verifies the contract and common functionality
that all transport implementations must follow.
"""

import pytest
from unittest.mock import Mock, patch
from models.mcp_models import MCPRequest, MCPResponse, MCPError
from transports.transport_interface import Transport, TransportInterface


class MockTransport(Transport):
    """
    模拟传输实现，用于测试基础传输类的功能
    
    这个类实现了所有抽象方法，用于测试Transport基类的通用功能。
    """
    
    def __init__(self):
        super().__init__()
        self.started = False
        self.stopped = False
        self.sent_responses = []
    
    def start(self) -> None:
        """启动模拟传输"""
        self.started = True
        self._running = True
    
    def stop(self) -> None:
        """停止模拟传输"""
        self.stopped = True
        self._running = False
    
    def send_response(self, response: MCPResponse) -> None:
        """记录发送的响应"""
        self.sent_responses.append(response)
    
    def get_connection_info(self) -> dict:
        """返回模拟连接信息"""
        return {
            "transport_type": "mock",
            "running": self._running,
            "started": self.started,
            "stopped": self.stopped
        }


class TestTransportInterface:
    """传输层接口测试"""
    
    def test_transport_interface_is_abstract(self):
        """测试传输接口是抽象类"""
        with pytest.raises(TypeError):
            TransportInterface()
    
    def test_transport_interface_methods_are_abstract(self):
        """测试接口方法都是抽象方法"""
        # 验证所有必需的抽象方法都存在
        abstract_methods = TransportInterface.__abstractmethods__
        expected_methods = {
            'start', 'stop', 'send_response', 
            'set_request_handler', 'is_running', 'get_connection_info'
        }
        assert abstract_methods == expected_methods


class TestTransportBaseClass:
    """传输基类测试"""
    
    def setup_method(self):
        """测试前设置"""
        self.transport = MockTransport()
    
    def test_initial_state(self):
        """测试初始状态"""
        assert not self.transport.is_running()
        assert self.transport._request_handler is None
        assert not self.transport.started
        assert not self.transport.stopped
    
    def test_set_request_handler(self):
        """测试设置请求处理器"""
        handler = Mock()
        self.transport.set_request_handler(handler)
        assert self.transport._request_handler == handler
    
    def test_start_stop_lifecycle(self):
        """测试启动停止生命周期"""
        # 初始状态
        assert not self.transport.is_running()
        
        # 启动
        self.transport.start()
        assert self.transport.is_running()
        assert self.transport.started
        
        # 停止
        self.transport.stop()
        assert not self.transport.is_running()
        assert self.transport.stopped
    
    def test_handle_request_with_handler(self):
        """测试有处理器时的请求处理"""
        # 设置模拟处理器
        mock_handler = Mock()
        expected_response = MCPResponse(id="test-123", result={"success": True})
        mock_handler.return_value = expected_response
        
        self.transport.set_request_handler(mock_handler)
        
        # 创建测试请求
        request = MCPRequest(
            id="test-123",
            method="test_method",
            params={"param1": "value1"}
        )
        
        # 处理请求
        response = self.transport._handle_request(request)
        
        # 验证结果
        assert response == expected_response
        mock_handler.assert_called_once_with(request)
    
    def test_handle_request_without_handler(self):
        """测试没有处理器时的请求处理"""
        request = MCPRequest(
            id="test-123",
            method="test_method",
            params={}
        )
        
        # 处理请求（没有设置处理器）
        response = self.transport._handle_request(request)
        
        # 验证返回错误响应
        assert response.id == request.id
        assert response.error is not None
        assert response.error.code == -32603  # Internal error
        assert response.error.data["details"] == "No request handler registered"
    
    def test_handle_request_handler_exception(self):
        """测试处理器抛出异常时的处理"""
        # 设置会抛出异常的处理器
        mock_handler = Mock()
        mock_handler.side_effect = ValueError("Test exception")
        
        self.transport.set_request_handler(mock_handler)
        
        request = MCPRequest(
            id="test-123",
            method="test_method",
            params={}
        )
        
        # 处理请求
        response = self.transport._handle_request(request)
        
        # 验证返回错误响应
        assert response.id == request.id
        assert response.error is not None
        assert response.error.code == -32602  # Invalid params (from error handler)
        assert "Request handling failed: Test exception" in response.error.data["details"]
    
    def test_get_connection_info(self):
        """测试获取连接信息"""
        info = self.transport.get_connection_info()
        
        assert isinstance(info, dict)
        assert info["transport_type"] == "mock"
        assert "running" in info
        assert "started" in info
        assert "stopped" in info
    
    def test_send_response(self):
        """测试发送响应"""
        response = MCPResponse(id="test-123", result={"data": "test"})
        
        self.transport.send_response(response)
        
        # 验证响应被记录
        assert len(self.transport.sent_responses) == 1
        assert self.transport.sent_responses[0] == response


class TestTransportIntegration:
    """传输层集成测试"""
    
    def setup_method(self):
        """测试前设置"""
        self.transport = MockTransport()
    
    def test_complete_request_response_cycle(self):
        """测试完整的请求响应周期"""
        # 设置处理器
        def test_handler(request: MCPRequest) -> MCPResponse:
            return MCPResponse(
                id=request.id,
                result={"method": request.method, "processed": True}
            )
        
        self.transport.set_request_handler(test_handler)
        self.transport.start()
        
        # 创建并处理请求
        request = MCPRequest(
            id="integration-test",
            method="test_integration",
            params={"test": True}
        )
        
        response = self.transport._handle_request(request)
        
        # 验证响应
        assert response.id == request.id
        assert response.result["method"] == "test_integration"
        assert response.result["processed"] is True
        assert response.error is None
        
        # 清理
        self.transport.stop()
    
    def test_multiple_requests_handling(self):
        """测试多个请求的处理"""
        # 设置计数处理器
        call_count = 0
        
        def counting_handler(request: MCPRequest) -> MCPResponse:
            nonlocal call_count
            call_count += 1
            return MCPResponse(
                id=request.id,
                result={"call_number": call_count}
            )
        
        self.transport.set_request_handler(counting_handler)
        self.transport.start()
        
        # 处理多个请求
        requests = [
            MCPRequest(id=f"req-{i}", method="count", params={})
            for i in range(3)
        ]
        
        responses = []
        for req in requests:
            resp = self.transport._handle_request(req)
            responses.append(resp)
        
        # 验证所有响应
        assert len(responses) == 3
        for i, resp in enumerate(responses):
            assert resp.id == f"req-{i}"
            assert resp.result["call_number"] == i + 1
        
        self.transport.stop()
    
    def test_error_recovery(self):
        """测试错误恢复能力"""
        error_count = 0
        
        def error_prone_handler(request: MCPRequest) -> MCPResponse:
            nonlocal error_count
            error_count += 1
            
            # 第一次调用抛出异常，第二次正常返回
            if error_count == 1:
                raise RuntimeError("Simulated error")
            
            return MCPResponse(
                id=request.id,
                result={"recovered": True, "attempt": error_count}
            )
        
        self.transport.set_request_handler(error_prone_handler)
        self.transport.start()
        
        # 第一个请求（会出错）
        request1 = MCPRequest(id="error-test-1", method="error_prone", params={})
        response1 = self.transport._handle_request(request1)
        
        assert response1.error is not None
        assert "Request handling failed: Simulated error" in response1.error.data["details"]
        
        # 第二个请求（应该成功）
        request2 = MCPRequest(id="error-test-2", method="error_prone", params={})
        response2 = self.transport._handle_request(request2)
        
        assert response2.error is None
        assert response2.result["recovered"] is True
        assert response2.result["attempt"] == 2
        
        self.transport.stop()


if __name__ == "__main__":
    pytest.main([__file__])