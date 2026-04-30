import os
import sys
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(current_dir, 'src')
sys.path.append(src_dir)

from cross_file_analyzer.cross_file_analyzer import CrossFileAnalyzer


def main():
    print("输入项目根目录绝对路径：")
    project_root = input()
    if not os.path.exists(project_root):
        print(f"{project_root}不存在")
        return
    analyzer=CrossFileAnalyzer(project_root)
    analyzer.analyze()
    analyzer.print_results()
    analyzer.print_all_asts()
if __name__ == "__main__":
    main()


#TODO:
#第一条:call节点在本地有定义 即使他的顶层库来自三方库也不算三方库的API
#第二条:call节点在本地找不到定义 看符号链 如果链上有Call节点在本地有定义也不算
#第三条：self处理
#第四条：链式调用a().b().c()拆分成a()、a().b()、a().b().c()