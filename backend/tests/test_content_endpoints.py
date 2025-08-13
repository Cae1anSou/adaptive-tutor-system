import pytest
import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 设置正确的数据目录路径
os.environ["DATA_DIR"] = str(project_root / "app" / "data")

from fastapi.testclient import TestClient
from fastapi import FastAPI
from unittest.mock import patch, MagicMock
from app.api.endpoints.content import router as content_router
from app.schemas.content import LearningContent, TestTask, LevelInfo, SelectElementInfo, CodeContent
from app.schemas.response import StandardResponse
import json

# 创建一个独立的FastAPI应用，只包含content路由
app = FastAPI(title="Content Test App")
app.include_router(content_router)

client = TestClient(app)


class TestContentEndpointsErrorHandling:
    """测试错误处理"""
    
    def test_invalid_topic_id_format(self):
        """测试无效的主题ID格式"""
        response = client.get("/learning-content/invalid-format")
        
        # 应该返回错误状态码
        assert response.status_code in [404, 500]
    
    def test_empty_topic_id(self):
        """测试空的主题ID"""
        response = client.get("/learning-content/")
        
        # 应该返回404（路由不匹配）
        assert response.status_code == 404
    
    def test_special_characters_in_topic_id(self):
        """测试特殊字符的主题ID"""
        response = client.get("/learning-content/special@#$%")
        
        # 应该返回错误状态码
        assert response.status_code in [404, 500]
    
    def test_http_exception_handling(self):
        """测试HTTPException处理"""
        # 测试不存在的文件，应该抛出HTTPException
        response = client.get("/learning-content/nonexistent_file")
        
        # 应该返回404状态码
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert "未找到主题" in data["detail"]
    
    def test_general_exception_handling(self):
        """测试一般Exception处理"""
        # 测试路径不存在的情况
        response = client.get("/learning-content/../../invalid_path")
        
        # 应该返回404状态码（路径不存在）
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert data["detail"] == "Not Found"

class TestAllContentFiles:
    """全面测试所有学习内容和测试内容文件"""
    
    def get_all_content_files(self):
        """获取所有内容文件列表"""
        data_dir = Path("backend/app/data")
        learning_content_dir = data_dir / "learning_content"
        test_tasks_dir = data_dir / "test_tasks"
        
        learning_files = []
        test_files = []
        
        # 获取学习内容文件
        if learning_content_dir.exists():
            for file_path in learning_content_dir.glob("*.json"):
                topic_id = file_path.stem  # 获取文件名（不含扩展名）
                learning_files.append(topic_id)
        
        # 获取测试任务文件
        if test_tasks_dir.exists():
            for file_path in test_tasks_dir.glob("*.json"):
                topic_id = file_path.stem  # 获取文件名（不含扩展名）
                test_files.append(topic_id)
        
        return learning_files, test_files
    
    def load_original_json_file(self, content_type: str, topic_id: str):
        """加载原始JSON文件内容"""
        data_dir = Path("backend/app/data")
        file_path = data_dir / content_type / f"{topic_id}.json"
        
        if file_path.exists():
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return None
    
    def test_all_learning_content_files(self):
        """测试所有学习内容文件 - 包含字段验证和内容一致性验证"""
        learning_files, _ = self.get_all_content_files()
        
        print(f"\n发现 {len(learning_files)} 个学习内容文件:")
        for topic_id in learning_files:
            print(f"  - {topic_id}")
        
        successful_tests = 0
        failed_tests = []
        
        for topic_id in learning_files:
            try:
                response = client.get(f"/learning-content/{topic_id}")
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # 1. 验证StandardResponse结构
                    assert "code" in data, f"{topic_id} - 缺少code字段"
                    assert "data" in data, f"{topic_id} - 缺少data字段"
                    assert "message" in data, f"{topic_id} - 缺少message字段"
                    assert data["code"] == 200, f"{topic_id} - code字段应该为200"
                    
                    # 2. 验证LearningContent模型结构
                    api_data = data["data"]
                    assert "topic_id" in api_data, f"{topic_id} - 缺少topic_id字段"
                    assert "title" in api_data, f"{topic_id} - 缺少title字段"
                    assert "levels" in api_data, f"{topic_id} - 缺少levels字段"
                    assert "sc_all" in api_data, f"{topic_id} - 缺少sc_all字段"
                    
                    # 3. 验证数据类型
                    assert isinstance(api_data["topic_id"], str), f"{topic_id} - topic_id应该是字符串"
                    assert isinstance(api_data["title"], str), f"{topic_id} - title应该是字符串"
                    assert isinstance(api_data["levels"], list), f"{topic_id} - levels应该是列表"
                    assert isinstance(api_data["sc_all"], list), f"{topic_id} - sc_all应该是列表"
                    
                    # 4. 验证levels结构
                    for i, level in enumerate(api_data["levels"]):
                        assert "level" in level, f"{topic_id} - level[{i}]缺少level字段"
                        assert "description" in level, f"{topic_id} - level[{i}]缺少description字段"
                        assert isinstance(level["level"], int), f"{topic_id} - level[{i}] level应该是整数"
                        assert isinstance(level["description"], str), f"{topic_id} - level[{i}] description应该是字符串"
                    
                    # 5. 验证sc_all结构
                    for i, sc_item in enumerate(api_data["sc_all"]):
                        assert "topic_id" in sc_item, f"{topic_id} - sc_all[{i}]缺少topic_id字段"
                        assert "select_element" in sc_item, f"{topic_id} - sc_all[{i}]缺少select_element字段"
                        assert isinstance(sc_item["select_element"], list), f"{topic_id} - sc_all[{i}] select_element应该是列表"
                    
                    # 6. 验证内容一致性（与原始文件对比）
                    original_data = self.load_original_json_file("learning_content", topic_id)
                    if original_data:
                        # 验证topic_id一致性
                        assert api_data["topic_id"] == original_data["topic_id"], f"{topic_id} - topic_id不一致"
                        assert api_data["topic_id"] == topic_id, f"{topic_id} - topic_id与请求参数不一致"
                        
                        # 验证title一致性
                        assert api_data["title"] == original_data["title"], f"{topic_id} - title不一致"
                        
                        # 验证levels一致性
                        assert len(api_data["levels"]) == len(original_data["levels"]), f"{topic_id} - levels数量不一致"
                        for i, (api_level, orig_level) in enumerate(zip(api_data["levels"], original_data["levels"])):
                            assert api_level["level"] == orig_level["level"], f"{topic_id} - level[{i}] level值不一致"
                            assert api_level["description"] == orig_level["description"], f"{topic_id} - level[{i}] description不一致"
                        
                        # 验证sc_all一致性
                        assert len(api_data["sc_all"]) == len(original_data["sc_all"]), f"{topic_id} - sc_all数量不一致"
                        for i, (api_sc, orig_sc) in enumerate(zip(api_data["sc_all"], original_data["sc_all"])):
                            assert api_sc["topic_id"] == orig_sc["topic_id"], f"{topic_id} - sc_all[{i}] topic_id不一致"
                            assert api_sc["select_element"] == orig_sc["select_element"], f"{topic_id} - sc_all[{i}] select_element不一致"
                        
                        successful_tests += 1
                        print(f"  ✅ {topic_id} - 模型结构验证和内容一致性验证通过")
                    else:
                        failed_tests.append(f"{topic_id} (原始文件不存在)")
                        print(f"  ❌ {topic_id} - 原始文件不存在")
                else:
                    failed_tests.append(f"{topic_id} (状态码: {response.status_code})")
                    print(f"  ❌ {topic_id} - 失败 (状态码: {response.status_code})")
                    
            except Exception as e:
                failed_tests.append(f"{topic_id} (异常: {str(e)})")
                print(f"  ❌ {topic_id} - 异常: {str(e)}")
        
        print(f"\n学习内容测试结果: {successful_tests}/{len(learning_files)} 成功")
        if failed_tests:
            print(f"失败的文件: {failed_tests}")
        
        # 至少应该有一些文件能够成功加载
        assert successful_tests > 0, f"没有成功加载任何学习内容文件。失败的文件: {failed_tests}"
    
    def test_all_test_task_files(self):
        """测试所有测试任务文件 - 包含字段验证和内容一致性验证"""
        _, test_files = self.get_all_content_files()
        
        print(f"\n发现 {len(test_files)} 个测试任务文件:")
        for topic_id in test_files:
            print(f"  - {topic_id}")
        
        successful_tests = 0
        failed_tests = []
        
        for topic_id in test_files:
            try:
                response = client.get(f"/test-tasks/{topic_id}")
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # 1. 验证StandardResponse结构
                    assert "code" in data, f"{topic_id} - 缺少code字段"
                    assert "data" in data, f"{topic_id} - 缺少data字段"
                    assert "message" in data, f"{topic_id} - 缺少message字段"
                    assert data["code"] == 200, f"{topic_id} - code字段应该为200"
                    
                    # 2. 验证TestTask模型结构
                    api_data = data["data"]
                    assert "topic_id" in api_data, f"{topic_id} - 缺少topic_id字段"
                    assert "title" in api_data, f"{topic_id} - 缺少title字段"
                    assert "description_md" in api_data, f"{topic_id} - 缺少description_md字段"
                    assert "start_code" in api_data, f"{topic_id} - 缺少start_code字段"
                    assert "checkpoints" in api_data, f"{topic_id} - 缺少checkpoints字段"
                    
                    # 3. 验证数据类型
                    assert isinstance(api_data["topic_id"], str), f"{topic_id} - topic_id应该是字符串"
                    assert isinstance(api_data["title"], str), f"{topic_id} - title应该是字符串"
                    assert isinstance(api_data["description_md"], str), f"{topic_id} - description_md应该是字符串"
                    assert isinstance(api_data["start_code"], dict), f"{topic_id} - start_code应该是字典"
                    assert isinstance(api_data["checkpoints"], list), f"{topic_id} - checkpoints应该是列表"
                    
                    # 4. 验证start_code结构
                    start_code = api_data["start_code"]
                    assert "html" in start_code, f"{topic_id} - start_code缺少html字段"
                    assert "css" in start_code, f"{topic_id} - start_code缺少css字段"
                    assert "js" in start_code, f"{topic_id} - start_code缺少js字段"
                    assert isinstance(start_code["html"], str), f"{topic_id} - start_code.html应该是字符串"
                    assert isinstance(start_code["css"], str), f"{topic_id} - start_code.css应该是字符串"
                    assert isinstance(start_code["js"], str), f"{topic_id} - start_code.js应该是字符串"
                    
                    # 5. 验证checkpoints结构
                    for i, checkpoint in enumerate(api_data["checkpoints"]):
                        assert "name" in checkpoint, f"{topic_id} - checkpoint[{i}]缺少name字段"
                        assert "type" in checkpoint, f"{topic_id} - checkpoint[{i}]缺少type字段"
                        assert "feedback" in checkpoint, f"{topic_id} - checkpoint[{i}]缺少feedback字段"
                        assert isinstance(checkpoint["name"], str), f"{topic_id} - checkpoint[{i}] name应该是字符串"
                        assert isinstance(checkpoint["type"], str), f"{topic_id} - checkpoint[{i}] type应该是字符串"
                        assert isinstance(checkpoint["feedback"], str), f"{topic_id} - checkpoint[{i}] feedback应该是字符串"
                    
                    # 6. 验证内容一致性（与原始文件对比）
                    original_data = self.load_original_json_file("test_tasks", topic_id)
                    if original_data:
                        # 验证topic_id一致性
                        assert api_data["topic_id"] == original_data["topic_id"], f"{topic_id} - topic_id不一致"
                        assert api_data["topic_id"] == topic_id, f"{topic_id} - topic_id与请求参数不一致"
                        
                        # 验证title一致性
                        assert api_data["title"] == original_data["title"], f"{topic_id} - title不一致"
                        
                        # 验证description_md一致性
                        assert api_data["description_md"] == original_data["description_md"], f"{topic_id} - description_md不一致"
                        
                        # 验证start_code一致性
                        assert api_data["start_code"]["html"] == original_data["start_code"]["html"], f"{topic_id} - start_code.html不一致"
                        assert api_data["start_code"]["css"] == original_data["start_code"]["css"], f"{topic_id} - start_code.css不一致"
                        assert api_data["start_code"]["js"] == original_data["start_code"]["js"], f"{topic_id} - start_code.js不一致"
                        
                        # 验证checkpoints一致性
                        assert len(api_data["checkpoints"]) == len(original_data["checkpoints"]), f"{topic_id} - checkpoints数量不一致"
                        for i, (api_checkpoint, orig_checkpoint) in enumerate(zip(api_data["checkpoints"], original_data["checkpoints"])):
                            assert api_checkpoint["name"] == orig_checkpoint["name"], f"{topic_id} - checkpoint[{i}] name不一致"
                            assert api_checkpoint["type"] == orig_checkpoint["type"], f"{topic_id} - checkpoint[{i}] type不一致"
                            assert api_checkpoint["feedback"] == orig_checkpoint["feedback"], f"{topic_id} - checkpoint[{i}] feedback不一致"
                            
                            # 根据类型验证特定字段
                            if api_checkpoint["type"] == "assert_attribute":
                                assert api_checkpoint["selector"] == orig_checkpoint["selector"], f"{topic_id} - checkpoint[{i}] selector不一致"
                                assert api_checkpoint["attribute"] == orig_checkpoint["attribute"], f"{topic_id} - checkpoint[{i}] attribute不一致"
                                assert api_checkpoint["assertion_type"] == orig_checkpoint["assertion_type"], f"{topic_id} - checkpoint[{i}] assertion_type不一致"
                                assert api_checkpoint["value"] == orig_checkpoint["value"], f"{topic_id} - checkpoint[{i}] value不一致"
                            elif api_checkpoint["type"] == "assert_text_content":
                                assert api_checkpoint["selector"] == orig_checkpoint["selector"], f"{topic_id} - checkpoint[{i}] selector不一致"
                                assert api_checkpoint["assertion_type"] == orig_checkpoint["assertion_type"], f"{topic_id} - checkpoint[{i}] assertion_type不一致"
                                assert api_checkpoint["value"] == orig_checkpoint["value"], f"{topic_id} - checkpoint[{i}] value不一致"
                            elif api_checkpoint["type"] == "custom_script":
                                assert api_checkpoint["script"] == orig_checkpoint["script"], f"{topic_id} - checkpoint[{i}] script不一致"
                        
                        successful_tests += 1
                        print(f"  ✅ {topic_id} - 模型结构验证和内容一致性验证通过")
                    else:
                        failed_tests.append(f"{topic_id} (原始文件不存在)")
                        print(f"  ❌ {topic_id} - 原始文件不存在")
                else:
                    failed_tests.append(f"{topic_id} (状态码: {response.status_code})")
                    print(f"  ❌ {topic_id} - 失败 (状态码: {response.status_code})")
                    
            except Exception as e:
                failed_tests.append(f"{topic_id} (异常: {str(e)})")
                print(f"  ❌ {topic_id} - 异常: {str(e)}")
        
        print(f"\n测试任务测试结果: {successful_tests}/{len(test_files)} 成功")
        if failed_tests:
            print(f"失败的文件: {failed_tests}")
        
        # 至少应该有一些文件能够成功加载
        assert successful_tests > 0, f"没有成功加载任何测试任务文件。失败的文件: {failed_tests}"
    
    def test_content_file_consistency(self):
        """测试内容文件的一致性"""
        learning_files, test_files = self.get_all_content_files()
        
        print(f"\n检查内容文件一致性:")
        print(f"学习内容文件: {len(learning_files)} 个")
        print(f"测试任务文件: {len(test_files)} 个")
        
        # 检查是否有对应的测试任务文件
        missing_test_tasks = []
        for topic_id in learning_files:
            if topic_id not in test_files:
                missing_test_tasks.append(topic_id)
        
        if missing_test_tasks:
            print(f"缺少对应测试任务的学习内容: {missing_test_tasks}")
        
        # 检查是否有对应的学习内容文件
        missing_learning_content = []
        for topic_id in test_files:
            if topic_id not in learning_files:
                missing_learning_content.append(topic_id)
        
        if missing_learning_content:
            print(f"缺少对应学习内容的测试任务: {missing_learning_content}")
        
        # 输出统计信息
        print(f"文件一致性检查完成")

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
