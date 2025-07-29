#!/bin/bash
# Git维护脚本 - 自动化常见的Git操作

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印带颜色的消息
print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# 检查Git状态
check_git_status() {
    print_info "检查Git仓库状态..."
    
    if ! git rev-parse --git-dir > /dev/null 2>&1; then
        print_error "当前目录不是Git仓库"
        exit 1
    fi
    
    # 检查是否有未提交的更改
    if ! git diff-index --quiet HEAD --; then
        print_warning "检测到未提交的更改"
        git status --short
        return 1
    fi
    
    print_success "Git仓库状态正常"
    return 0
}

# 自动提交当前更改
auto_commit() {
    print_info "自动提交当前更改..."
    
    # 检查是否有更改
    if git diff-index --quiet HEAD --; then
        print_info "没有检测到更改"
        return 0
    fi
    
    # 显示更改
    echo "检测到以下更改:"
    git status --short
    
    # 询问是否继续
    read -p "是否继续提交这些更改? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_info "取消提交"
        return 1
    fi
    
    # 获取提交消息
    read -p "请输入提交消息: " commit_message
    if [ -z "$commit_message" ]; then
        commit_message="🔧 Auto commit: $(date '+%Y-%m-%d %H:%M:%S')"
    fi
    
    # 添加所有更改并提交
    git add .
    git commit -m "$commit_message"
    print_success "提交完成: $commit_message"
}

# 创建新的功能分支
create_feature_branch() {
    print_info "创建新的功能分支..."
    
    # 确保在develop分支
    current_branch=$(git branch --show-current)
    if [ "$current_branch" != "develop" ]; then
        print_info "切换到develop分支..."
        git checkout develop
        git pull origin develop 2>/dev/null || print_warning "无法从远程拉取develop分支"
    fi
    
    # 获取分支名称
    read -p "请输入功能分支名称 (不包含feature/前缀): " branch_name
    if [ -z "$branch_name" ]; then
        print_error "分支名称不能为空"
        return 1
    fi
    
    full_branch_name="feature/$branch_name"
    
    # 创建并切换到新分支
    git checkout -b "$full_branch_name"
    print_success "创建并切换到分支: $full_branch_name"
}

# 合并功能分支到develop
merge_feature_branch() {
    print_info "合并功能分支到develop..."
    
    current_branch=$(git branch --show-current)
    
    # 检查是否在功能分支
    if [[ ! $current_branch =~ ^feature/ ]]; then
        print_error "当前不在功能分支上"
        return 1
    fi
    
    # 检查是否有未提交的更改
    if ! check_git_status; then
        print_error "请先提交所有更改"
        return 1
    fi
    
    # 切换到develop并合并
    git checkout develop
    git pull origin develop 2>/dev/null || print_warning "无法从远程拉取develop分支"
    git merge "$current_branch"
    
    # 询问是否删除功能分支
    read -p "是否删除功能分支 $current_branch? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        git branch -d "$current_branch"
        print_success "已删除分支: $current_branch"
    fi
    
    print_success "功能分支合并完成"
}

# 创建版本标签
create_version_tag() {
    print_info "创建版本标签..."
    
    # 确保在main分支
    current_branch=$(git branch --show-current)
    if [ "$current_branch" != "main" ]; then
        print_warning "建议在main分支创建版本标签"
        read -p "是否继续? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            return 1
        fi
    fi
    
    # 检查是否有未提交的更改
    if ! check_git_status; then
        print_error "请先提交所有更改"
        return 1
    fi
    
    # 获取版本号
    read -p "请输入版本号 (例如: v1.0.0): " version
    if [ -z "$version" ]; then
        print_error "版本号不能为空"
        return 1
    fi
    
    # 获取版本描述
    read -p "请输入版本描述: " description
    if [ -z "$description" ]; then
        description="Release $version"
    fi
    
    # 创建标签
    git tag -a "$version" -m "$description"
    print_success "创建标签: $version"
    
    # 询问是否推送到远程
    read -p "是否推送标签到远程仓库? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        git push origin "$version"
        print_success "标签已推送到远程仓库"
    fi
}

# 清理本地分支
cleanup_branches() {
    print_info "清理已合并的本地分支..."
    
    # 获取已合并到develop的分支
    merged_branches=$(git branch --merged develop | grep -v -E "(develop|main|\*)" | xargs)
    
    if [ -z "$merged_branches" ]; then
        print_info "没有需要清理的分支"
        return 0
    fi
    
    echo "以下分支已合并到develop:"
    echo "$merged_branches"
    
    read -p "是否删除这些分支? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "$merged_branches" | xargs git branch -d
        print_success "分支清理完成"
    fi
}

# 显示帮助信息
show_help() {
    echo "Git维护脚本 - 使用方法:"
    echo ""
    echo "  $0 status          - 检查Git状态"
    echo "  $0 commit          - 自动提交当前更改"
    echo "  $0 feature         - 创建新的功能分支"
    echo "  $0 merge           - 合并功能分支到develop"
    echo "  $0 tag             - 创建版本标签"
    echo "  $0 cleanup         - 清理已合并的本地分支"
    echo "  $0 help            - 显示此帮助信息"
    echo ""
}

# 主函数
main() {
    case "${1:-help}" in
        "status")
            check_git_status
            ;;
        "commit")
            auto_commit
            ;;
        "feature")
            create_feature_branch
            ;;
        "merge")
            merge_feature_branch
            ;;
        "tag")
            create_version_tag
            ;;
        "cleanup")
            cleanup_branches
            ;;
        "help"|*)
            show_help
            ;;
    esac
}

# 执行主函数
main "$@"
