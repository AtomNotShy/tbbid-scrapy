#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
个人业绩数据存储功能测试脚本
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from xizang.models.models import PersonPerformance, CompanyInfo
from xizang.settings import POSTGRES_URL


def test_person_performance_storage():
    """测试个人业绩数据存储"""
    # 建立数据库连接
    engine = create_engine(POSTGRES_URL)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        # 查询个人业绩数据
        performance_count = session.query(PersonPerformance).count()
        print(f"个人业绩记录总数: {performance_count}")
        
        # 查询最近的5条个人业绩记录
        recent_performances = session.query(PersonPerformance).order_by(
            PersonPerformance.updated_at.desc()
        ).limit(5).all()
        
        print("\n最近的5条个人业绩记录:")
        print("-" * 80)
        for perf in recent_performances:
            print(f"姓名: {perf.name}")
            print(f"公司代码: {perf.corp_code}")
            print(f"公司名称: {perf.corp_name}")
            print(f"项目名称: {perf.project_name}")
            print(f"数据等级: {perf.data_level}")
            print(f"角色: {perf.role}")
            print(f"更新时间: {perf.updated_at}")
            print("-" * 80)
        
        # 按公司统计个人业绩数量
        company_performance_stats = session.execute(text("""
            SELECT corp_name, COUNT(*) as performance_count
            FROM person_performance 
            GROUP BY corp_name 
            ORDER BY performance_count DESC 
            LIMIT 10
        """)).fetchall()
        
        print("\n公司个人业绩统计 (前10名):")
        print("-" * 50)
        for company, count in company_performance_stats:
            print(f"{company}: {count} 条业绩记录")
        
        # 按角色统计
        role_stats = session.execute(text("""
            SELECT role, COUNT(*) as count
            FROM person_performance 
            GROUP BY role 
            ORDER BY count DESC
        """)).fetchall()
        
        print("\n按角色统计:")
        print("-" * 30)
        for role, count in role_stats:
            print(f"{role}: {count} 条记录")
            
    except Exception as e:
        print(f"查询错误: {e}")
    finally:
        session.close()


def test_data_integrity():
    """测试数据完整性"""
    engine = create_engine(POSTGRES_URL)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        # 检查是否有孤立的个人业绩记录（公司不存在）
        orphaned_performances = session.execute(text("""
            SELECT p.name, p.corp_code, p.corp_name
            FROM person_performance p
            LEFT JOIN company_info c ON p.corp_code = c.corp_code
            WHERE c.corp_code IS NULL
            LIMIT 10
        """)).fetchall()
        
        print("\n数据完整性检查:")
        print("-" * 40)
        if orphaned_performances:
            print("发现孤立的个人业绩记录:")
            for name, corp_code, corp_name in orphaned_performances:
                print(f"  - {name} ({corp_code}) - {corp_name}")
        else:
            print("✓ 所有个人业绩记录都有对应的公司信息")
        
        # 检查重复记录
        duplicate_performances = session.execute(text("""
            SELECT name, corp_code, project_name, role, COUNT(*) as count
            FROM person_performance
            GROUP BY name, corp_code, project_name, role
            HAVING COUNT(*) > 1
            LIMIT 10
        """)).fetchall()
        
        if duplicate_performances:
            print("\n发现重复的个人业绩记录:")
            for name, corp_code, project, role, count in duplicate_performances:
                print(f"  - {name} ({corp_code}) - {project} - {role}: {count} 条重复")
        else:
            print("✓ 没有发现重复的个人业绩记录")
            
    except Exception as e:
        print(f"完整性检查错误: {e}")
    finally:
        session.close()


if __name__ == "__main__":
    print("=" * 80)
    print("个人业绩数据存储功能测试")
    print("=" * 80)
    
    test_person_performance_storage()
    test_data_integrity()
    
    print("\n测试完成!") 