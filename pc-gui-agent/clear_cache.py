"""
清理Python缓存
"""
import os
import shutil
from pathlib import Path

def clear_pycache():
    """清理所有__pycache__目录和.pyc文件"""
    base_dir = Path(__file__).parent
    src_dir = base_dir / "src"
    
    removed = []
    for root, dirs, files in os.walk(src_dir):
        # 删除__pycache__目录
        if "__pycache__" in dirs:
            cache_dir = Path(root) / "__pycache__"
            shutil.rmtree(cache_dir)
            removed.append(str(cache_dir))
            dirs.remove("__pycache__")
        
        # 删除.pyc文件
        for file in files:
            if file.endswith(".pyc"):
                pyc_file = Path(root) / file
                pyc_file.unlink()
                removed.append(str(pyc_file))
    
    if removed:
        print(f"已清理 {len(removed)} 个缓存文件/目录:")
        for item in removed[:10]:  # 只显示前10个
            print(f"  - {item}")
        if len(removed) > 10:
            print(f"  ... 还有 {len(removed) - 10} 个")
    else:
        print("没有找到缓存文件")

if __name__ == "__main__":
    clear_pycache()
    print("\n缓存清理完成！")

