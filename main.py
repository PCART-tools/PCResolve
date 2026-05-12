import os
import sys
current_dir=os.path.dirname(os.path.abspath(__file__))
src_dir=os.path.join(current_dir, 'src')
sys.path.append(src_dir)

from cross_file_analyzer.cross_file_analyzer import CrossFileAnalyzer


def main():
    print("输入项目根目录绝对路径：")
    project_root=input()
    if not os.path.exists(project_root):
        print(f"{project_root}不存在")
        return
    analyzer=CrossFileAnalyzer(project_root)
    analyzer.analyze()
    analyzer.print_results()
    analyzer.print_all_asts()
if __name__=="__main__":
    main()