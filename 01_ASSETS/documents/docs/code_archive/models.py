"""
火斗云智企业一体化管理系统 - 数据模型
8大模块：CRM/项目/OA/HRM/进销存/财务/派单/系统
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, JSON, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from backend.database import Base

# ============ 系统模块 ============
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True)
    name = Column(String(50))
    role = Column(String(20), default="员工")  # 管理员/部门经理/员工
    department = Column(String(50))
    phone = Column(String(20))
    email = Column(String(100))
    status = Column(String(20), default="在职")
    created_at = Column(DateTime, default=datetime.now)

# ============ CRM客户管理 ============
class Customer(Base):
    __tablename__ = "crm_customers"
    id = Column(Integer, primary_key=True, index=True)
    customer_no = Column(String(30), unique=True, index=True)
    name = Column(String(100))
    contact_person = Column(String(50))
    phone = Column(String(20))
    email = Column(String(100))
    address = Column(String(200))
    industry = Column(String(50))
    level = Column(String(20), default="普通")  # VIP/重要/普通/潜在
    source = Column(String(50))  # 来源
    owner = Column(String(50))  # 负责人
    status = Column(String(20), default="跟进中")  # 跟进中/已成交/已流失
    remark = Column(Text)
    created_at = Column(DateTime, default=datetime.now)

class Lead(Base):
    __tablename__ = "crm_leads"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100))
    phone = Column(String(20))
    source = Column(String(50))
    status = Column(String(20), default="新线索")  # 新线索/跟进中/已转化/已放弃
    owner = Column(String(50))
    remark = Column(Text)
    created_at = Column(DateTime, default=datetime.now)

class Opportunity(Base):
    __tablename__ = "crm_opportunities"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100))
    customer_id = Column(Integer, ForeignKey("crm_customers.id"))
    customer_name = Column(String(100))
    amount = Column(Float, default=0)
    stage = Column(String(20), default="初步接触")
    probability = Column(Integer, default=10)
    owner = Column(String(50))
    expected_close_date = Column(DateTime)
    remark = Column(Text)
    created_at = Column(DateTime, default=datetime.now)

class Contract(Base):
    __tablename__ = "crm_contracts"
    id = Column(Integer, primary_key=True, index=True)
    contract_no = Column(String(30), unique=True, index=True)
    name = Column(String(100))
    customer_id = Column(Integer, ForeignKey("crm_customers.id"))
    customer_name = Column(String(100))
    amount = Column(Float, default=0)
    sign_date = Column(DateTime)
    start_date = Column(DateTime)
    end_date = Column(DateTime)
    status = Column(String(20), default="执行中")
    owner = Column(String(50))
    remark = Column(Text)
    created_at = Column(DateTime, default=datetime.now)

# ============ 项目管理 ============
class Project(Base):
    __tablename__ = "pm_projects"
    id = Column(Integer, primary_key=True, index=True)
    project_no = Column(String(30), unique=True, index=True)
    name = Column(String(100))
    customer = Column(String(100))
    manager = Column(String(50))
    members = Column(JSON, default=list)
    status = Column(String(20), default="进行中")  # 规划中/进行中/已完成/已暂停
    priority = Column(String(20), default="普通")
    start_date = Column(DateTime)
    end_date = Column(DateTime)
    progress = Column(Integer, default=0)  # 进度%
    budget = Column(Float, default=0)
    remark = Column(Text)
    created_at = Column(DateTime, default=datetime.now)

class Task(Base):
    __tablename__ = "pm_tasks"
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("pm_projects.id"))
    name = Column(String(100))
    assignee = Column(String(50))
    status = Column(String(20), default="待开始")  # 待开始/进行中/已完成/已延期
    priority = Column(String(20), default="普通")
    due_date = Column(DateTime)
    completed_at = Column(DateTime)
    remark = Column(Text)
    created_at = Column(DateTime, default=datetime.now)

# ============ OA办公自动化 ============
class Approval(Base):
    __tablename__ = "oa_approvals"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(100))
    type = Column(String(30))  # 请假/报销/采购/合同/用章/其他
    applicant = Column(String(50))
    department = Column(String(50))
    amount = Column(Float, default=0)
    status = Column(String(20), default="审批中")  # 草稿/审批中/已通过/已驳回
    current_approver = Column(String(50))
    approval_history = Column(JSON, default=list)
    content = Column(Text)
    created_at = Column(DateTime, default=datetime.now)

class Announcement(Base):
    __tablename__ = "oa_announcements"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(100))
    type = Column(String(20), default="通知")  # 通知/公告/制度/活动
    content = Column(Text)
    publisher = Column(String(50))
    is_top = Column(Boolean, default=False)
    status = Column(String(20), default="已发布")
    created_at = Column(DateTime, default=datetime.now)

# ============ HRM人力资源 ============
class Department(Base):
    __tablename__ = "hrm_departments"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True)
    manager = Column(String(50))
    parent_id = Column(Integer, default=0)
    description = Column(String(200))
    created_at = Column(DateTime, default=datetime.now)

class Employee(Base):
    __tablename__ = "hrm_employees"
    id = Column(Integer, primary_key=True, index=True)
    employee_no = Column(String(30), unique=True, index=True)
    name = Column(String(50))
    gender = Column(String(10))
    phone = Column(String(20))
    email = Column(String(100))
    department = Column(String(50))
    position = Column(String(50))
    level = Column(String(20), default="P1")
    entry_date = Column(DateTime)
    status = Column(String(20), default="在职")  # 在职/试用期/离职/休假
    salary = Column(Float, default=0)
    created_at = Column(DateTime, default=datetime.now)

class Attendance(Base):
    __tablename__ = "hrm_attendances"
    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("hrm_employees.id"))
    employee_name = Column(String(50))
    date = Column(String(20))  # YYYY-MM-DD
    check_in = Column(String(20))
    check_out = Column(String(20))
    status = Column(String(20), default="正常")  # 正常/迟到/早退/缺勤/请假/出差
    work_hours = Column(Float, default=0)
    remark = Column(String(200))
    created_at = Column(DateTime, default=datetime.now)

# ============ 进销存 ============
class Product(Base):
    __tablename__ = "inv_products"
    id = Column(Integer, primary_key=True, index=True)
    product_no = Column(String(30), unique=True, index=True)
    name = Column(String(100))
    category = Column(String(50))
    spec = Column(String(100))
    unit = Column(String(20))
    purchase_price = Column(Float, default=0)
    sale_price = Column(Float, default=0)
    stock = Column(Integer, default=0)
    warning_stock = Column(Integer, default=10)
    status = Column(String(20), default="在售")
    created_at = Column(DateTime, default=datetime.now)

class PurchaseOrder(Base):
    __tablename__ = "inv_purchases"
    id = Column(Integer, primary_key=True, index=True)
    purchase_no = Column(String(30), unique=True, index=True)
    supplier = Column(String(100))
    product_id = Column(Integer, ForeignKey("inv_products.id"))
    product_name = Column(String(100))
    quantity = Column(Integer, default=0)
    unit_price = Column(Float, default=0)
    total_amount = Column(Float, default=0)
    status = Column(String(20), default="待入库")  # 待入库/已入库/已取消
    operator = Column(String(50))
    remark = Column(Text)
    created_at = Column(DateTime, default=datetime.now)

class SaleOrder(Base):
    __tablename__ = "inv_sales"
    id = Column(Integer, primary_key=True, index=True)
    sale_no = Column(String(30), unique=True, index=True)
    customer = Column(String(100))
    product_id = Column(Integer, ForeignKey("inv_products.id"))
    product_name = Column(String(100))
    quantity = Column(Integer, default=0)
    unit_price = Column(Float, default=0)
    total_amount = Column(Float, default=0)
    status = Column(String(20), default="待发货")  # 待发货/已发货/已完成/已取消
    operator = Column(String(50))
    remark = Column(Text)
    created_at = Column(DateTime, default=datetime.now)

# ============ 财务管理 ============
class FinanceRecord(Base):
    __tablename__ = "fin_records"
    id = Column(Integer, primary_key=True, index=True)
    record_no = Column(String(30), unique=True, index=True)
    type = Column(String(20))  # 收入/支出
    category = Column(String(50))  # 销售收入/采购支出/工资/办公费/差旅费/其他
    amount = Column(Float, default=0)
    related_order = Column(String(50))
    operator = Column(String(50))
    status = Column(String(20), default="已确认")
    remark = Column(Text)
    record_date = Column(String(20))
    created_at = Column(DateTime, default=datetime.now)

# ============ 派单系统（整合） ============
class WorkOrder(Base):
    __tablename__ = "dispatch_orders"
    id = Column(Integer, primary_key=True, index=True)
    order_no = Column(String(30), unique=True, index=True)
    customer_name = Column(String(100))
    customer_phone = Column(String(20))
    address = Column(String(200))
    latitude = Column(Float, default=22.5431)
    longitude = Column(Float, default=114.0579)
    work_type = Column(String(50))
    priority = Column(String(20), default="普通")
    status = Column(String(20), default="待派单")  # 待派单/已派单/已接单/施工中/已完工/已验收/已取消
    assignee = Column(String(50))
    assignee_id = Column(Integer)
    skill_required = Column(JSON, default=list)
    material_cost = Column(Float, default=0)
    labor_cost = Column(Float, default=0)
    total_cost = Column(Float, default=0)
    commission = Column(Float, default=0)
    rating = Column(Integer, default=0)
    remark = Column(Text)
    created_at = Column(DateTime, default=datetime.now)
    accepted_at = Column(DateTime)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)

class Worker(Base):
    __tablename__ = "dispatch_workers"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50))
    phone = Column(String(20))
    level = Column(String(20), default="初级")  # 初级/中级/高级/专家
    skills = Column(JSON, default=list)
    certifications = Column(JSON, default=list)
    status = Column(String(20), default="空闲")  # 空闲/施工中/休假/离职
    latitude = Column(Float, default=22.5431)
    longitude = Column(Float, default=114.0579)
    current_order_count = Column(Integer, default=0)
    max_load = Column(Integer, default=5)
    performance_score = Column(Float, default=80)
    good_rate = Column(Float, default=90)
    total_orders = Column(Integer, default=0)
    total_commission = Column(Float, default=0)
    created_at = Column(DateTime, default=datetime.now)

# 所有模型列表（用于init_db）
all_models = [
    User, Customer, Lead, Opportunity, Contract,
    Project, Task, Approval, Announcement,
    Department, Employee, Attendance,
    Product, PurchaseOrder, SaleOrder,
    FinanceRecord, WorkOrder, Worker
]
