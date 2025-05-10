from decimal import Decimal
import random
import string
from flask import Flask, jsonify, render_template, request, session, url_for, redirect, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from flask_wtf import FlaskForm
import pytz
from wtforms import StringField, SubmitField, IntegerField, DecimalField, PasswordField
from wtforms.validators import DataRequired, Email
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from sqlalchemy import func
import re   


app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret-key-goes-here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///inventory.db'
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# # Bảng Người dùng
class User(UserMixin, db.Model):
    id       = db.Column(db.Integer, primary_key=True)
    email    = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    name     = db.Column(db.String(100), nullable=False)

VIETNAM_TZ = pytz.timezone("Asia/Ho_Chi_Minh")
def vietnam_now():
    """Return the current time in Vietnam timezone."""
    return datetime.now(VIETNAM_TZ)

product_batch_materials = db.Table('product_batch_materials',
    db.Column('product_batch_id', db.Integer, db.ForeignKey('product_batches.batch_id'), primary_key=True),
    db.Column('inventory_id', db.Integer, db.ForeignKey('inventory.stockTran_id'), primary_key=True)
)
class Import(db.Model):
    __tablename__ = 'imports'
    import_id = db.Column(db.Integer, primary_key=True, autoincrement=True)    
    # Material info
    material_name = db.Column(db.String(255), nullable=False)
    material_description = db.Column(db.String(255))
    quantity_in_stock = db.Column(db.Integer, default=0)
    reorder_level = db.Column(db.Integer, default=30)    
    # Supplier info
    sup_name = db.Column(db.String(255), nullable=False)
    sup_contact_info = db.Column(db.String(255), nullable=False)
    sup_address = db.Column(db.String(255), nullable=False)    
    status = db.Column(db.String(50), default="Supplying")
    section_name = db.Column(db.String(255))  # Section name for classification
    category = db.Column(db.String(255))  # Category of the material

    def __repr__(self):
        return f'<Import {self.import_id}>'

class Order(db.Model):
    __tablename__ = 'orders'
    order_id = db.Column(db.Integer, primary_key=True)
    cus_name = db.Column(db.String(255), nullable=False)  # Customer Name
    cus_contact = db.Column(db.String(255), nullable=False)  # Customer Contact
    cus_address = db.Column(db.String(255), nullable=False)  # Customer Address
    order_date = db.Column(db.DateTime, default=vietnam_now)
    price = db.Column(db.Numeric(10, 2), nullable=False)
    deposit_amount = db.Column(db.Float, nullable=False, default=0.0)
    deposit_percent = db.Column(db.Float, nullable=False, default=0.0)
    orprice=db.Column(db.Numeric(10, 2), nullable=False)


    status = db.Column(db.String(50), default="Processing")

    order_details = db.relationship('OrderDetail', backref='order_relation', lazy=True)

    def __repr__(self):
        return f'<Order {self.order_id}>'
def add_monthly_data():
    
    current_year = datetime.now().year
    months = [f"{current_year}-{str(month).zfill(2)}" for month in range(1, 4)] 
    for month in months:
        existing_month_data = db.session.query(Order).filter(Order.order_date.like(f'{month}%')).first()        
        if not existing_month_data:
            order_date = datetime.strptime(f"{month}-01", "%Y-%m-%d")  
            new_order = Order(
                cus_name="Default Customer",
                cus_contact="Default Contact",
                cus_address="Default Address",
                order_date=order_date,  
                price=100000000,
                deposit_amount=2000000,
                status="Delivered",
                orprice=100000000
            )
            db.session.add(new_order)
            print(f"Đã thêm dữ liệu mặc định cho tháng {month}")
    db.session.commit()
@app.before_request
def initialize_data():
    add_monthly_data()

class InventoryProduct(db.Model):
    __tablename__ = 'inventorypro'
    id = db.Column(db.Integer, primary_key=True)  # Unique ID for the inventory record
    product_name = db.Column(db.String(255), nullable=False)  # Name of the product
    quantity = db.Column(db.Integer, nullable=False, default=0)  # Quantity of the product in stock    
    date = db.Column(db.DateTime, default=vietnam_now)  # Date of transaction
    def __repr__(self):
        return f'<InventoryProduct {self.product_name}>'

class Inventory(db.Model):
    __tablename__ = 'inventory'
    stockTran_id = db.Column(db.Integer, primary_key=True)  # Unique ID for the inventory record
    product_name = db.Column(db.String(255), nullable=False)  # Name of the product
    quantity = db.Column(db.Integer, nullable=False, default=0)  # Quantity of the product in stock
    transaction_type = db.Column(db.String(50), nullable=False)  # "Addition" or "Removal"
    transaction_date = db.Column(db.DateTime, default=vietnam_now)  # Date of transaction
    

    import_id = db.Column(db.Integer, db.ForeignKey('imports.import_id'), nullable=False)  # Foreign Key to Import (raw material)

    # Relationship to Import (Material)
    import_data = db.relationship('Import', backref='inventory_records', lazy=True)
    category = db.Column(db.String(255))
    warehouse=db.Column(db.String(255))

    def __repr__(self):
        return f'<Inventory {self.product_name}>'

class DepositConfirm(db.Model):
    __tablename__ = 'deposit_confirm'
    id = db.Column(db.Integer, primary_key=True)  # Khoá chính của bảng
    order_id = db.Column(db.Integer, db.ForeignKey('orders.order_id'), nullable=False)  # Mã đơn hàng (khóa ngoại)
    deposit_amount = db.Column(db.Numeric(10, 2), nullable=False)  # Số tiền gửi
    transaction_date = db.Column(db.DateTime, default=vietnam_now)  # Ngày giao dịch

    order = db.relationship('Order', backref='deposit_confirm')  # Quan hệ với bảng Order

    def __repr__(self):
        return f'<DepositConfirm {self.id}>'

class OrderDetail(db.Model):
    __tablename__ = 'order_details'

    order_detail_id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.order_id'))
    product_name = db.Column(db.String(100))
    product_price = db.Column(db.Float)
    quantity = db.Column(db.Integer)
    odstarus=db.Column(db.String(50), default="Processing")
    import_id = db.Column(db.Integer, db.ForeignKey('imports.import_id'))  # Import relation

    # Relationship to Import
    import_record = db.relationship('Import', backref='order_details', lazy=True)
    

    def __repr__(self):
        return f'<OrderDetail {self.orderdetail_id}>'

class ProductBatch(db.Model):
    __tablename__ = 'product_batches'
    batch_id = db.Column(db.Integer, primary_key=True)
    batch_number = db.Column(db.Integer, nullable=False)
    category = db.Column(db.String(100))

    # Liên kết với OrderDetail để lấy thông tin sản phẩm
    order_detail_id = db.Column(db.Integer, db.ForeignKey('order_details.order_detail_id'))
    order_detail = db.relationship('OrderDetail', backref='product_batches')

    quantity_completed = db.Column(db.Integer, default=0)    

    manufacturing_status = db.Column(db.String(50), default='In Production')
    product_condition = db.Column(db.String(50), nullable=True)
    defect_reason = db.Column(db.String(255), nullable=True)
   
    start_time = db.Column(db.DateTime,default=vietnam_now)  # Thêm trường thời gian bắt đầu
    end_time = db.Column(db.DateTime,default=vietnam_now) 
    quantity_to_update=db.Column(db.Integer, default=0)

    inventory = db.relationship('Inventory', secondary=product_batch_materials, backref='product_batches')
    price = db.Column(db.Float)

    def __repr__(self):
        return f"<Batch #{self.batch_id} - OrderDetail #{self.order_detail_id}>"
    
    def is_complete(self):       
        return self.quantity_in_production == self.quantity_completed

class ShippingQueue(db.Model):
    __tablename__ = 'shipping_queue'
    shipping_queue_id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.order_id'))
    batch_id = db.Column(db.Integer, db.ForeignKey('product_batches.batch_id'))
    product_name = db.Column(db.String(255), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(50), default='Processing')  
    price = db.Column(db.Float)

    
    # Thiết lập quan hệ với bảng ProductBatch và Order
    order_detail = db.relationship('Order', backref='shipping_queue')
    product_batch = db.relationship('ProductBatch', backref='shipping_queue')

    def __repr__(self):
        return f"<ShippingQueue {self.shipping_queue_id} - Order {self.order_id} - Batch {self.batch_id}>"

class Shipping(db.Model):
    __tablename__ = 'shipping'
    shipping_id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.order_id'))
    tracking_code = db.Column(db.String(255), unique=True)
    provider = db.Column(db.String(255), nullable=False)
    shipping_cost = db.Column(db.Numeric(10, 2), nullable=False)
    shipping_status = db.Column(db.String(50), default='Processing')  # Status: Pending, Shipped, Delivered
    pay_method=db.Column(db.String(255), nullable=False)
    shipment_time = db.Column(db.DateTime, default=vietnam_now)
    order = db.relationship('Order', backref='shipping_details')
    price = db.Column(db.Float)
    quan = db.Column(db.Numeric(10, 2), nullable=False)
    status = db.Column(db.String(50), default='Processing')

    def __repr__(self):
        return f"<Shipping {self.shipping_id} - Order {self.order_id}>"

class PurchaseRequest(db.Model):
    __tablename__      = 'purchase_request'
    id                 = db.Column(db.Integer, primary_key=True)
    import_id           = db.Column(db.Integer, db.ForeignKey('imports.import_id'))
    quantity_requested = db.Column(db.Integer, nullable=False)
    transaction_date   = db.Column(db.DateTime, default=vietnam_now)

    import_request = db.relationship('Import', backref='order_request', lazy=True)

    def __repr__(self):
        return f'<PurchaseRequest {self.id}>'

class ReturnRequest(db.Model):
    __tablename__ = 'return_requests'
    return_id = db.Column(db.Integer, primary_key=True)
    order_detail_id = db.Column(db.Integer, db.ForeignKey('order_details.order_detail_id'))
    return_status = db.Column(db.String(50), default='Pending')  
    condition = db.Column(db.String(50)) 
    defect_reason = db.Column(db.String(255))  
    inspection_date = db.Column(db.DateTime, default=vietnam_now)
    refund_method  = db.Column(db.String(100))     
    quan = db.Column(db.Numeric(10, 2), nullable=False)
  
    order_detail = db.relationship('OrderDetail', backref='return_requests')
    


# Khởi tạo Database
with app.app_context():
    # db.drop_all() 
    db.create_all()


@app.route('/')
@login_required
def index():
    return render_template('index.html', logged_in=current_user.is_authenticated)

@app.route('/register', methods=["GET", "POST"])
def register():
    if request.method == "POST":
        email = request.form.get('email')
        result = db.session.execute(db.select(User).where(User.email == email))
        user = result.scalar()
        if user:
            flash("You've already signed up with that email, log in instead!")
            return redirect(url_for('login'))
        hash_and_salted_password = generate_password_hash(
            request.form.get('password'),
            method='pbkdf2:sha256',
            salt_length=8
        )
        new_user = User(
            email=request.form.get('email'),
            password=hash_and_salted_password,
            name=request.form.get('name'),
        )
        db.session.add(new_user)
        db.session.commit()
        login_user(new_user)
        flash('Account created successfully') 
        return redirect(url_for("login"))
      
    return render_template("login.html", logged_in=current_user.is_authenticated)

@app.route('/login', methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get('email')
        password = request.form.get('password')
        result = db.session.execute(db.select(User).where(User.email == email))
        user = result.scalar()
        if not user:
            flash("That email does not exist, please try again.")
            return redirect(url_for('login'))
        elif not check_password_hash(user.password, password):
            flash('Password incorrect, please try again.')
            return redirect(url_for('login'))
        else:
            login_user(user)
            # flash('Account created successfully')
            return redirect(url_for('dashboard'))
    # Passing True or False if the user is authenticated.
    return render_template("login.html", logged_in=current_user.is_authenticated)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

def get_daily_sales_data():
    """Fetch sales data grouped by day within each month"""
    daily_sales_data = db.session.query(
        db.func.strftime('%Y-%m', Order.order_date).label('month_year'),
        db.func.strftime('%d', Order.order_date).label('day'),
        db.func.sum(Order.orprice).label('total_sales')
    ).filter(
       (Order.status == 'Delivered') | (Order.status == 'Cancelled')
    ).group_by(
        db.func.strftime('%Y-%m', Order.order_date),
        db.func.strftime('%d', Order.order_date)
    ).all()
    
    return [
        {
            'month': row.month_year.split('-')[1], 
            'day': row.day,                         
            'total_sales': float(row.total_sales) if row.total_sales else 0.0
        }
        for row in daily_sales_data
    ]

def get_sales_data():
    sales_data = db.session.query(
        db.func.strftime('%Y-%m', Order.order_date).label('month'),
        db.func.sum(Order.orprice).label('total_sales')
    ).filter(
        Order.status == 'Delivered'  
    ).group_by(
        db.func.strftime('%Y-%m', Order.order_date)
    ).all()
    return [
        {
            'month': row.month.split('-')[1],
            'total_sales': float(row.total_sales) if row.total_sales else 0.0
        }
        for row in sales_data
    ]

def get_top_selling_products():
    top_products = db.session.query(
        OrderDetail.product_name,
        db.func.sum(OrderDetail.quantity).label('total_quantity')
    ).filter(
        OrderDetail.odstarus == 'Done'  
    ).group_by(
        OrderDetail.product_name
    ).order_by(
        db.func.sum(OrderDetail.quantity).desc()
    ).limit(3).all()
    return [
        {
            'product_name': row.product_name,
            'total_quantity': row.total_quantity
        }
        for row in top_products
    ]


@app.route('/dashboard/')
@login_required
def dashboard():
    sales_data = get_sales_data()
    daily_sales_data = get_daily_sales_data()  
    top_products = get_top_selling_products()

    return render_template(
        'dashboard.html',
        sales_data=sales_data,
        daily_sales_data=daily_sales_data,  
        top_products=top_products
    )

@app.route('/order_status_data')
def get_order_status_data():
    date_filter = request.args.get('date_filter', 'day') 
    order_status_data = db.session.query(
        Order.status,
        func.count(Order.order_id)  
    ).group_by(Order.status).all()
    return jsonify([{'status': row.status, 'count': row[1]} for row in order_status_data])

@app.route('/inventorypro/')
@login_required
def view_inventorypro():
    inventorypro = InventoryProduct.query.all()
    return render_template("inventoryPro.html", inventorypro=inventorypro )

@app.route('/inventory/')
@login_required
def view_inventory():
    inventory = Inventory.query.all()
    low_stock_items = [item for item in inventory if item.quantity <= item.import_data.reorder_level]
    imports = Import.query.all()
    return render_template("inventory.html", inventory=inventory, imports=imports,low_stock_items=low_stock_items )

@app.route('/classify-warehouse/<int:inventory_id>', methods=["POST"])
@login_required
def classify_warehouse(inventory_id):
    inventory_item = Inventory.query.get_or_404(inventory_id)
    warehouse = request.form.get('warehouse')  # Lấy warehouse từ form
    inventory_item.warehouse = warehouse  # Cập nhật warehouse cho item
    db.session.commit()  # Lưu thay đổi vào cơ sở dữ liệu
    flash(f"Material {inventory_item.product_name} classified as {warehouse}.", "success")
    return redirect(url_for('view_inventory'))

@app.route('/classify-material/<int:inventory_id>', methods=["POST"])
@login_required
def classify_material(inventory_id):
    inventory_item = Inventory.query.get_or_404(inventory_id)
    category = request.form.get('category')
    inventory_item.category = category  # Update the category in the database
    db.session.commit()
    flash(f"Material {inventory_item.product_name} classified as {category}.", "success")
    return redirect(url_for('view_inventory'))

@app.route('/delete-inventory/<int:inventory_id>', methods=["POST"])
@login_required
def delete_inventory(inventory_id):
    inventory_item = Inventory.query.get_or_404(inventory_id)

    try:
        # Delete the inventory record
        db.session.delete(inventory_item)
        db.session.commit()  # Commit the changes to the database

        flash("Inventory item deleted successfully.", "success")
    except Exception as e:
        db.session.rollback()  # Rollback the session in case of an error
        flash(f"Error deleting inventory item: {str(e)}", "danger")

    return redirect(url_for('view_inventory'))  # Redirect back to the inventory page

@app.route('/create_purchase_request/<int:import_id>', methods=["GET", "POST"])
@login_required
def create_purchase_request(import_id):
    import_request = Import.query.get_or_404(import_id)
    inventory = Inventory.query.get_or_404(import_id)

    # Kiểm tra nếu số lượng còn thiếu và nhỏ hơn reorder level
    if inventory.quantity < import_request.reorder_level:
        # Tính toán số lượng cần nhập
        quantity_needed = import_request.reorder_level - inventory.quantity

        # Chuyển hướng đến trang add-import với các thông tin cần thiết đã được điền sẵn
        return redirect(url_for('add_imports', 
                                material_name=inventory.product_name,  # Sử dụng product_name từ Inventory
                                material_description=import_request.material_description,
                                reorder_level=import_request.reorder_level,
                                quantity_needed=quantity_needed,
                                sup_name=import_request.sup_name,
                                sup_contact_info=import_request.sup_contact_info,
                                sup_address=import_request.sup_address))

    flash("Stock level is sufficient. No purchase request needed.", "info")
    return redirect(url_for('view_inventory'))


@app.route('/add-imports/', methods=["GET", "POST"])
@login_required
def add_imports():
    if request.method == "POST":
        material_name = request.form["material_name"]     

        material_description = request.form.get("material_description", "")
        quantity_in_stock = int(request.form.get("quantity_in_stock", 0))
        if  int(quantity_in_stock) <= 0:
            flash("Value must be greater than 0.", "danger")
            return render_template("add-imports.html")
        reorder_level = int(request.form.get("reorder_level", 30))
        
        sup_name = request.form["sup_name"]
        sup_contact_info = request.form["sup_contact_info"]
        sup_address = request.form["sup_address"]

        # Create a new Import record
        new_import = Import(
            material_name=material_name,
            material_description=material_description,
            quantity_in_stock=quantity_in_stock,
            reorder_level=reorder_level,
            sup_name=sup_name,
            sup_contact_info=sup_contact_info,
            sup_address=sup_address,
            status="Supplying"
        )

        try:
            db.session.add(new_import)
            db.session.commit()
            flash("Import added successfully!", "success")
            return redirect(url_for('view_import'))  # Redirect to the page showing imports
        except Exception as e:
            db.session.rollback()
            flash(f"Error adding import: {str(e)}", "danger")

    # Get the pre-filled values from the query string
    material_name = request.args.get('material_name')
    material_description = request.args.get('material_description')
    reorder_level = request.args.get('reorder_level', type=int, default=30)
    quantity_needed = request.args.get('quantity_needed', type=int, default=0)
    sup_name=request.args.get('sup_name')
    sup_contact_info=request.args.get('sup_contact_info')
    sup_address=request.args.get('sup_address')

    return render_template("add-imports.html", 
                           material_name=material_name, 
                           material_description=material_description,
                           reorder_level=reorder_level, 
                           prefilled_quantity=quantity_needed,
                           sup_address=sup_address,
                           sup_contact_info=sup_contact_info,
                           sup_name=sup_name                           
                           )

@app.route('/add-import/', methods=["GET", "POST"])
@login_required
def add_import():
    if request.method == "POST":
        material_name = request.form["material_name"]
        
        # Validate material_name to only allow alphabets (no numbers or special characters)
        if not material_name.isalpha():
            flash("Material name should only contain alphabets.", "danger")
            return render_template("add-imports.html")
        
        material_description = request.form.get("material_description", "")
        quantity_in_stock = request.form.get("quantity_in_stock", 0)
        
        # Validate quantity_in_stock to ensure it's a number greater than 0
        if not quantity_in_stock.isdigit() or int(quantity_in_stock) <= 0:
            flash("Quantity in stock must be a number greater than 0.", "danger")
            return render_template("add-imports.html")
        
        reorder_level = int(request.form.get("reorder_level", 30))
        
        sup_name = request.form["sup_name"]
        sup_contact_info = request.form["sup_contact_info"]
        sup_address = request.form["sup_address"]

        # Create a new Import record
        new_import = Import(
            material_name=material_name,
            material_description=material_description,
            quantity_in_stock=int(quantity_in_stock),  # Convert to integer here after validation
            reorder_level=reorder_level,
            sup_name=sup_name,
            sup_contact_info=sup_contact_info,
            sup_address=sup_address,
            status="Supplying"
        )

        try:
            db.session.add(new_import)
            db.session.commit()
            flash("Import added successfully!", "success")
            return redirect(url_for('view_import'))  
        except Exception as e:
            db.session.rollback()
            flash(f"Error adding import: {str(e)}", "danger")
    return render_template("add-import.html")  

@app.route('/update-import-status/<int:import_id>', methods=["POST"])
@login_required
def update_import_status(import_id):
    import_record = Import.query.get_or_404(import_id)
    if import_record.status == "Supplying":
        import_record.status = "Supplied"
        existing_inventory_item = Inventory.query.filter_by(product_name=import_record.material_name).first()
        if existing_inventory_item:
            existing_inventory_item.quantity += import_record.quantity_in_stock  
            flash(f"Material {import_record.material_name} quantity updated in inventory.", "success")  
        else:
            new_inventory_item = Inventory(
                product_name=import_record.material_name,
                quantity=import_record.quantity_in_stock,
                transaction_type="Addition",  # Thêm vào kho
                import_id=import_record.import_id,
            )
            db.session.add(new_inventory_item)
            db.session.commit()
            flash(f"Material {import_record.material_name} quantity updated in inventory.", "success")  
            return redirect(url_for('view_import'))            
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            flash(f"Error updating status or adding to inventory: {str(e)}", "danger")
    elif import_record.status == "Supply":
        import_record.status = "Supplied"
        existing_inventory_item = Inventory.query.filter_by(product_name=import_record.material_name).first()
        if existing_inventory_item:
            existing_inventory_item.quantity = import_record.quantity_in_stock  # Chỉ cập nhật bằng số lượng hiện tại
            flash(f"Material {import_record.material_name} quantity updated in inventory.", "success")        
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            flash(f"Error updating status or adding to inventory: {str(e)}", "danger")
    else:
        flash("The import is already marked as 'Supplied'.", "warning")

    return redirect(url_for('view_import'))


@app.route('/update-import/<int:import_id>', methods=["POST", "GET"])
@login_required
def update_import(import_id):
    import_record = Import.query.get_or_404(import_id)
    if request.method == "POST":
        # Cập nhật thông tin import
        import_record.material_name = request.form['material_name']
        import_record.material_description = request.form.get('material_description', '')
        import_record.quantity_in_stock = int(request.form.get('quantity_in_stock', 0))
        import_record.reorder_level = int(request.form.get('reorder_level', 30))
        import_record.sup_name = request.form['sup_name']
        import_record.sup_contact_info = request.form['sup_contact_info']
        import_record.sup_address = request.form['sup_address']

        inventory_item = Inventory.query.filter_by(import_id=import_record.import_id).first()
        if inventory_item:
            if import_record.status=='Supplied':
                import_record.status='Supply'
                db.session.commit()
            else:
                inventory_item.quantity = import_record.quantity_in_stock  
                db.session.commit()
            flash("Material updated successfully !", "success")
            return redirect(url_for('view_import'))      
        return redirect(url_for('view_import'))
    return render_template("update-import.html", import_record=import_record)

@app.route('/delete-import/<int:import_id>', methods=["POST"])
@login_required
def delete_import(import_id):
    import_record = Import.query.get_or_404(import_id)
    inventory_items = Inventory.query.filter_by(import_id=import_id).all()
    for item in inventory_items:
        db.session.delete(item) 

    try:
        db.session.delete(import_record)
        db.session.commit()
        flash("Import deleted successfully!", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error deleting import: {str(e)}", "danger")

    return redirect(url_for('view_import'))

@app.route('/import/', methods=["GET", "POST"])
@login_required
def view_import():
    if request.method == "POST":
        material_name = request.form["material_name"]
        material_description = request.form.get("material_description", "")
        quantity_in_stock = int(request.form.get("quantity_in_stock", 0))
        reorder_level = int(request.form.get("reorder_level", 30))
        
        sup_name = request.form["sup_name"]
        sup_contact_info = request.form["sup_contact_info"]
        sup_address = request.form["sup_address"]
        
        new_import = Import(
            material_name=material_name,
            material_description=material_description,
            quantity_in_stock=quantity_in_stock,
            reorder_level=reorder_level,
            sup_name=sup_name,
            sup_contact_info=sup_contact_info,
            sup_address=sup_address
        )

        try:
            db.session.add(new_import)
            db.session.commit()
            flash("Import added successfully!", "success")
            return redirect(url_for('view_import'))
        except Exception as e:
            db.session.rollback()
            flash(f"Error adding import: {str(e)}", "danger")

    imports = Import.query.all()
    return render_template("import.html", imports=imports)



@app.route('/add-order/', methods=["GET", "POST"])
@login_required
def add_order():
    if request.method == "POST":
        # Retrieve customer information
        cus_name = request.form["cus_name"]
        cus_contact = request.form.get("cus_contact", "")
        cus_address = request.form.get("cus_address", "")

        if re.search(r'\d', cus_name):
            flash("Customer Name cannot contain numbers.", "danger")
            return redirect(url_for('add_order'))

        # Validate customer contact (required)
        if not cus_contact:
            flash("Customer contact is required.", "danger")
            return redirect(url_for('add_order'))
        
        # Handle price validation
        price = request.form.get("price")
        if not price:
            flash("Total Price is required.", "danger")
            return redirect(url_for('add_order'))
        
        price = float(price)

        # Handle order date parsing
        order_date_str = request.form.get("order_date")
        if not order_date_str:
            order_date = vietnam_now()
        else:
            order_date = vietnam_now.strptime(order_date_str, '%Y-%m-%dT%H:%M')

        # Retrieve deposit percentage from the form
        deposit_percent = request.form.get("deposit_percent", 0)
        deposit_percent = float(deposit_percent)  # Ensure it's a float

        # Calculate deposit amount based on the price and deposit percentage
        deposit_amount = (price * deposit_percent) / 100

        # Create new order record
        new_order = Order(
            cus_name=cus_name,
            cus_contact=cus_contact,
            cus_address=cus_address,
            price=price,
            order_date=order_date,
            deposit_amount=deposit_amount  ,
            deposit_percent=deposit_percent,
            orprice=price
        )
        db.session.add(new_order)
        db.session.commit()

        # Retrieve product information for multiple products
        product_names = request.form.getlist("product_name[]")
        product_prices = request.form.getlist("product_price[]")
        quantities = request.form.getlist("quantity[]")

        total_price = 0  # Initialize total price

        # Ensure that all product fields are filled in
        if not all([product_names, product_prices, quantities]):
            flash("All product fields are required.", "danger")
            return redirect(url_for('add_order'))

        # Process each product and add it to the order details
        for product_name, product_price, quantity in zip(product_names, product_prices, quantities):
            if not product_name or not product_price or not quantity:
                continue  # Skip empty product details if any field is empty

            product_price = float(product_price)
            quantity = int(quantity)

            # Add order detail for each product
            order_detail = OrderDetail(
                order_id=new_order.order_id,
                product_name=product_name,
                product_price=product_price,
                quantity=quantity
            )
            db.session.add(order_detail)

            # Add to total price
            total_price += product_price * quantity

        # Update the total price of the order
        new_order.price = total_price
        db.session.commit()

        flash("Order added successfully!", "success")
        return redirect("/order/")

    return render_template('add-order.html')

@app.template_filter('format_price')
@login_required
def format_price(value):
    try:
        if value >= 1000000000:
            return "{:,.2f} B".format(value / 1000000000)          
        elif value >= 1000000:
            return "{:,.2f} M".format(value / 1000000) 
        return "{:,.2f}".format(value)
    except (ValueError, TypeError):
        return value


@app.route('/order/', methods=["GET", "POST"])
@login_required
def view_order():
    orders = Order.query.all()    
    return render_template("order.html", orders=orders)

@app.route("/order-detail/<int:order_id>")
@login_required
def order_detail(order_id):
    order = Order.query.get_or_404(order_id)
    return render_template("order-detail.html", order=order)

@app.route("/update-order/<int:order_id>", methods=["POST", "GET"])
@login_required
def updateOrder(order_id):
    order = Order.query.get_or_404(order_id)

    if request.method == "POST":
        # Cập nhật thông tin khách hàng
        order.cus_name = request.form['cus_name']
        order.cus_contact = request.form['cus_contact']
        order.cus_address = request.form['cus_address']

        # Cập nhật chi tiết đơn hàng (sản phẩm)
        product_names = request.form.getlist('product_names[]')
        product_prices = request.form.getlist('product_prices[]')
        quantities = request.form.getlist('quantities[]')

        total_price = 0  # Khởi tạo giá trị tổng đơn hàng

        # Cập nhật thông tin sản phẩm và tính lại tổng giá trị đơn hàng
        for order_detail, product_name, product_price, quantity in zip(order.order_details, product_names, product_prices, quantities):
            order_detail.product_name = product_name
            order_detail.product_price = float(product_price)  # Convert giá trị sản phẩm thành float
            order_detail.quantity = int(quantity)  # Convert số lượng thành int

            # Cập nhật lại tổng giá trị đơn hàng
            total_price += order_detail.product_price * order_detail.quantity

        # Cập nhật giá trị tổng cho đơn hàng
        order.price = total_price

        try:
            db.session.commit()
            flash("Order updated successfully!", "success")
            return redirect("/order/")  # Chuyển hướng đến danh sách đơn hàng
        except Exception as e:
            db.session.rollback()
            flash(f"There was an issue while updating the order: {str(e)}", "danger")

    return render_template("update-order.html", order=order)

@app.route("/delete-order/<int:order_id>", methods=["GET", "POST"])
@login_required
def deleteOrder(order_id):
    order_to_delete = Order.query.get_or_404(order_id)

    try:
        # Nếu đơn hàng có chi tiết, cần xóa các chi tiết đơn hàng trước
        if order_to_delete.order_details:
            for detail in order_to_delete.order_details:
                db.session.delete(detail)  # Xóa chi tiết đơn hàng liên quan
        db.session.delete(order_to_delete)  # Xóa đơn hàng
        db.session.commit()  # Lưu thay đổi vào cơ sở dữ liệu
        flash("Order deleted successfully!", "success")
        return redirect("/order/")  # Quay lại danh sách đơn hàng

    except Exception as e:
        db.session.rollback()  # Rollback nếu có lỗi
        flash(f"There was an issue while deleting the order: {str(e)}", "danger")  # Hiển thị lỗi
        return redirect("/order/")  # Quay lại danh sách đơn hàng


@app.route('/add-product-batch/', methods=["GET", "POST"])
@login_required
def add_product_batch():
    order_details = OrderDetail.query.all()
    inventory = Inventory.query.all()

    if request.method == "POST":
        order_detail_id = request.form['order_detail_id']
        batch_number = int(request.form['batch_number'])
        category = request.form['category']
        material_ids = request.form.getlist('material_ids')  # List of material IDs

         # Check if the batch count is a positive number
        if batch_number <= 0:
            flash("Batch count must be greater than 0.", 'danger')
            return redirect(url_for('add_product_batch'))

        order_detail = OrderDetail.query.get(order_detail_id)
        if not order_detail:
            flash("Invalid order detail selected.", 'danger')
            return redirect(url_for('add_product_batch'))
        
        created_batches = []
        for i in range(batch_number):
            batch_number = f"Batch-{len(OrderDetail.query.get(order_detail_id).product_batches) + i + 1}"

            # Create a new product batch
            new_batch = ProductBatch(
                order_detail_id=order_detail_id,
                batch_number=batch_number,
                category=category,
                price=order_detail.product_price 
            )

            # Link materials to the batch (many-to-many relationship)
            for material_id in material_ids:
                import_data = Inventory.query.get(material_id)
                if import_data:
                    new_batch.inventory.append(import_data)

            try:
                db.session.add(new_batch)
                created_batches.append(new_batch)
            except Exception as e:
                db.session.rollback()
                flash(f"Error adding batch {batch_number}: {str(e)}", 'danger')
                return redirect(url_for('add_product_batch'))

        try:
            db.session.commit()
            flash(f"{len(created_batches)} product batches added successfully.", 'success')
            return redirect(url_for('view_product_batches'))
        except Exception as e:
            db.session.rollback()
            flash(f"Error: {str(e)}", 'danger')

    return render_template('add_product_batch.html', order_details=order_details, inventory=inventory)

@app.route('/delete-product-batch/<int:batch_id>', methods=["POST"])
@login_required
def delete_product_batch(batch_id):
    try:
        batch_to_delete = ProductBatch.query.get(batch_id)
        if batch_to_delete:
            # Remove relationships (if any) or perform any necessary clean-up
            db.session.delete(batch_to_delete)
            db.session.commit()
            flash("Product batch deleted successfully.", 'success')
        else:
            flash("Batch not found.", 'danger')
    except Exception as e:
        db.session.rollback()
        flash(f"Error: {str(e)}", 'danger')

    return redirect(url_for('view_product_batches'))

@app.route('/view-product-batches/', methods=["GET"])
@login_required
def view_product_batches():
    product_batches = ProductBatch.query.all()
    return render_template('view_product_batches.html', product_batches=product_batches)

@app.route('/update-quantity-produced/<int:batch_id>', methods=["GET", "POST"])
@login_required
def update_quantity_produced(batch_id):
    product_batch = ProductBatch.query.get(batch_id)
    if not product_batch:
        flash("Product batch not found.", 'danger')
        return redirect(url_for('view_product_batches'))

    order_detail = product_batch.order_detail  # Order related to the batch

    if request.method == "POST":
        # Nhập số lượng sản phẩm đã sản xuất
        quantity_to_update = int(request.form.get('quantity_to_update', 0))  # Quantity produced for this batch     
        total_produced = sum(batch.quantity_completed for batch in order_detail.product_batches)
        
        
        if total_produced + quantity_to_update > order_detail.quantity:
            flash("Invalid quantity.", 'danger')
            return redirect(url_for('view_product_batches'))
        
        if product_batch.start_time is None:
             product_batch.start_time = vietnam_now()

       
        product_batch.end_time = vietnam_now()

        # Cập nhật số lượng sản phẩm đã sản xuất cho batch
        product_batch.quantity_completed = quantity_to_update  # Update quantity_completed with the new value

        # Cập nhật số lượng trong kho (trừ số lượng tương ứng từ kho)
        for inventory_record in product_batch.inventory:  # Many-to-many relationship now
            if inventory_record.quantity >= quantity_to_update:
                # Trừ số lượng trong kho và bản ghi nhập
                inventory_record.quantity -= quantity_to_update
            else:
                flash(f"Not enough stock in inventory for material: {inventory_record.product_name}.", 'danger')
                return redirect(url_for('view_product_batches'))
        try:
            db.session.commit()
            flash("Quantity produced updated successfully and inventory updated.", 'success')
        except Exception as e:
            db.session.rollback()
            flash(f"Error updating inventory: {str(e)}", 'danger')
            return redirect(url_for('view_product_batches'))

        # Tính tổng số sản phẩm đã sản xuất (tổng tất cả các batch)
        total_produced = sum(batch.quantity_completed for batch in order_detail.product_batches)

        # Nếu total_produced >= order_detail.quantity, set status thành "Completed"
        if total_produced >= order_detail.quantity:
            product_batch.manufacturing_status = "Ready for Ship"
            db.session.commit()

            # Hiển thị nút "Ship" cho người dùng khi trạng thái là "Completed"
            flash(f"Batch {product_batch.batch_number} is completed, click 'Ship' to process it for shipping.", 'success')
        else:
            remaining_quantity = order_detail.quantity - total_produced
            product_batch.manufacturing_status = "Ready for Ship"
            db.session.commit()

            flash(f"Batch {product_batch.batch_number} in production, remaining: {remaining_quantity}", 'warning')

        return redirect(url_for('view_product_batches'))  # Quay lại trang quản lý sản xuất

    return render_template('view_product_batches.html', product_batch=product_batch)

@app.route('/ship-product-batch/<int:batch_id>', methods=["POST"])
@login_required
def ship_product_batch(batch_id):
    product_batch = ProductBatch.query.get(batch_id)
    if not product_batch:
        flash("Product batch not found.", 'danger')
        return redirect(url_for('view_product_batches'))

    order_detail = product_batch.order_detail

    # Chuyển trạng thái của batch thành "Processing"
    product_batch.manufacturing_status = "Completed"
    db.session.commit()

    # Tính tổng số lượng cho shipping
    total_quantity_for_shipping = sum(batch.quantity_completed for batch in order_detail.product_batches)

    shipping_queue_item = ShippingQueue(
        order_id=product_batch.order_detail.order_id,
        batch_id=product_batch.batch_id,
        product_name=product_batch.order_detail.product_name,
        quantity=product_batch.quantity_completed,
        status="Processing" ,
        price= product_batch.quantity_completed * product_batch.price
    )
    db.session.add(shipping_queue_item)
    db.session.commit()

    flash(f"Product batch {product_batch.batch_number} moved to shipping queue for Order #{product_batch.order_detail.order_id}.", 'success')

    return redirect(url_for('view_product_batches'))




@app.route('/shipping-queue/', methods=["GET"])
@login_required
def shipping_queue_list():
    shipping_queue_items = ShippingQueue.query.filter(ShippingQueue.status == "Processing").all()

    return render_template('shipping_queue.html', shipping_queue_items=shipping_queue_items)

@app.route('/create-shipping-order/<int:order_id>', methods=["GET", "POST"])
@login_required
def create_shipping_order(order_id):
    order = Order.query.get_or_404(order_id)
    shipping_queue_items = ShippingQueue.query.filter_by(order_id=order.order_id).all()
    if request.method == "POST":
        provider = request.form['provider']
        pay_method = request.form['pay_method']
        shipping_cost = request.form.get('shipping_cost', type=float)
        shipment_time = request.form.get('shipment_time') 
        price=request.form.get('price') 
        if not provider:
            flash("Shipping provider must be selected.", "danger")
            return redirect(url_for('create_shipping_order', order_id=order_id))
        if shipping_cost is None or shipping_cost <= 0:
            flash("Shipping cost must be a positive value.", "danger")
            return redirect(url_for('create_shipping_order', order_id=order_id))
        for shipping_queue_item in shipping_queue_items:
                shipping_queue_item.status = "Done"
        
        tracking_code = generate_tracking_code()
        shipping = Shipping(
            order_id=order_id,
            provider=provider,
            tracking_code=tracking_code,
            shipping_cost=shipping_cost,
            pay_method=pay_method,
            shipping_status="Processing",
            shipment_time=shipment_time,
            status="Processing"
            )

        try:
            db.session.add(shipping)
            shipping.quan=shipping_queue_item.quantity
            shipping.price=shipping_queue_item.price
            db.session.commit()

            flash(f"Shipping order created for Order #{order_id} with tracking code {tracking_code}.", 'success')
            return redirect(url_for('shipping_list', shipping_id=shipping.shipping_id))
        except Exception as e:
            db.session.rollback()
            flash(f"Error creating shipping order: {str(e)}", 'danger')
    
    return render_template('create_shipping_order.html', order=order)
def generate_tracking_code():
    length = 10
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

@app.route('/confirm-shipping-payment/<int:shipping_id>', methods=["POST", "GET"])
@login_required
def confirm_shipping_payment(shipping_id):
    shipping = Shipping.query.get_or_404(shipping_id)
    order = Order.query.get_or_404(shipping.order_id)
    shipping_queue = ShippingQueue.query.filter_by(order_id=order.order_id).all()
    order_details = OrderDetail.query.filter_by(order_id=order.order_id).all()
    product_batches = ProductBatch.query.filter(
        ProductBatch.order_detail_id.in_([od.order_detail_id for od in order_details])
    ).all()

    if request.method == "POST":
        try:            
            payment_amount = float(request.form['payment_amount'])
            if payment_amount < shipping.shipping_cost:
                flash("Insufficient payment for shipping.", "danger")
                return redirect(url_for('confirm_shipping_payment', shipping_id=shipping_id))
            shipping.shipping_status = "Paid"
            for shipping_queue_item in shipping_queue:
                shipping_queue_item.status = "Delivered"
            all_shippings = Shipping.query.filter_by(order_id=order.order_id).all()
            if all(s.shipping_status == "Paid" or s.shipping_status =="Cancelled" for s in all_shippings) and \
               all(pb.manufacturing_status == "Completed" for pb in product_batches):
                order.status = "Delivered"
                shipping.status="Done"
                for od in order_details:
                    od.odstarus = "Done"
            db.session.commit()
            flash("Shipping payment confirmed. Shipping marked as Paid.", "success")
            return redirect(url_for('view_shipping', shipping_id=shipping_id))
        except ValueError:
            flash("Invalid payment amount. Please enter a valid number.", "danger")
        except Exception as e:
            db.session.rollback()
            flash(f"Error during payment confirmation: {str(e)}", 'danger') 

    deposit = (shipping.price * shipping.order.deposit_percent) / 100
    total_payment_amount = int(float(shipping.shipping_cost) + float(deposit))   
    
    return render_template(
        'confirm_shipping_payment.html',
        shipping=shipping,
        deposit=deposit,
        total_payment_amount=total_payment_amount,
        shipping_queue=shipping_queue
    )


@app.route('/shipping-list/', methods=["GET"])
@login_required
def shipping_list():
    page = request.args.get('page', 1, type=int)
    shippings = Shipping.query.paginate(page=page, per_page=10)
    return render_template('shipping-list.html', shippings=shippings)

@app.route('/delete-shipping-list/<int:shipping_id>', methods=["POST"])
@login_required
def delete_shipping_list(shipping_id):
    shipping = Shipping.query.get_or_404(shipping_id)
    try:
        db.session.delete(shipping)
        db.session.commit()
        flash(f"Shipping queue item #{shipping_id} deleted successfully.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error deleting shipping queue item: {str(e)}", "danger")
    return redirect(url_for('shipping_list'))

@app.route('/shipping/<int:shipping_id>', methods=["GET"])
@login_required
def view_shipping(shipping_id):
    shipping = Shipping.query.get_or_404(shipping_id)
    return render_template('view_shipping.html', shipping=shipping)

@app.route('/cancel-shipping/<int:shipping_id>', methods=["POST"])
@login_required
def cancel_shipping(shipping_id):
    shipping = Shipping.query.get_or_404(shipping_id)    
    order = Order.query.get_or_404(shipping.order_id)
    if shipping.shipping_status != "Processing" and shipping.shipping_status !="Paid" :
        flash("This shipping order cannot be canceled because it is either already  canceled.", "danger")
        return redirect(url_for('view_shipping', shipping_id=shipping_id))
    try:
        shipping.shipping_status = "Cancell"
        if (shipping.shipping_status == "Cancell") :
            order.status="Cancelled"
        db.session.commit()
        flash("Shipping order has been successfully canceled.", "success")
    except Exception as e:
        db.session.rollback()  
        flash(f"Error canceling shipping: {str(e)}", "danger")
    return redirect(url_for('view_shipping', shipping_id=shipping_id))

@app.route('/delete-shipping-queue/<int:shipping_queue_id>', methods=["POST"])
@login_required
def delete_shipping_queue(shipping_queue_id):
    shipping_queue_item = ShippingQueue.query.get_or_404(shipping_queue_id)
    try:
        db.session.delete(shipping_queue_item)
        db.session.commit()
        flash(f"Shipping queue item #{shipping_queue_id} deleted successfully.", "success")
    except Exception as e:
        db.session.rollback()  
        flash(f"Error deleting shipping queue item: {str(e)}", "danger")
    return redirect(url_for('shipping_queue_list'))



@app.route('/returns/')
@login_required
def returns():
    return_request = ReturnRequest.query.all()    
    shipping = Shipping.query.all()
    return render_template("returns.html",return_request=return_request, shipping=shipping  )

@app.route('/create-return/<int:shipping_id>', methods=['GET', 'POST'])
def create_return(shipping_id):

    shipping = Shipping.query.get_or_404(shipping_id)   
    order = Order.query.get_or_404(shipping.order_id)    
    shipping.shipping_status = "Cancelled"    
    total_amount = shipping.price    
    deposit_percent = shipping.order.deposit_percent or 0
    deposit_amount = (total_amount * deposit_percent) / 100
    deficit_amount = total_amount - deposit_amount
    deficit_amounts = Decimal(deficit_amount)
    total_amounts= Decimal(total_amount)

    # Tạo yêu cầu trả lại
    new_return = ReturnRequest(
        order_detail_id=shipping.order_id,
        return_status='Cancelled',          
        refund_method=deficit_amount,     
        quan=shipping.quan
    )

    # Cập nhật giá trị price trong order
    if shipping.status == "Done":
        order.orprice = order.orprice - deficit_amounts
    elif shipping.status == "Processing":
        order.orprice = order.orprice - total_amounts

    # Cập nhật thông tin vào cơ sở dữ liệu
    db.session.commit()  # Commit các thay đổi trước khi thêm yêu cầu trả lại

    db.session.add(new_return)
    db.session.commit()  # Commit lần nữa để lưu yêu cầu trả lại

    # Hiển thị thông báo và chuyển hướng
    flash('Return request created successfully!', 'success')
    return redirect(url_for('returns'))


@app.route('/classify-condition/<int:return_id>', methods=["POST"])
@login_required
def classify_condition(return_id):
    return_request = ReturnRequest.query.get_or_404(return_id)
    order_detail= OrderDetail.query.get_or_404(return_request.return_id)    
    condition = request.form.get('condition')
    return_request.condition = condition
    db.session.commit()
    if condition == "Good":
        inventory_product = InventoryProduct(
            product_name=order_detail.product_name,
            quantity=float(return_request.quan),  
            date=vietnam_now() ,          
            
        )
        db.session.add(inventory_product)
        db.session.commit()

    return redirect(url_for('returns'))

@app.route('/classify_defect_reason/<int:return_id>', methods=["POST"])
@login_required
def classify_defect_reason(return_id):
    return_request = ReturnRequest.query.get_or_404(return_id)  
    defect_reason = request.form.get('defect_reason')  
    return_request.defect_reason = defect_reason  
    db.session.commit()          
    return redirect(url_for('returns')) 

@app.route('/view-return-request/<int:return_id>', methods=["GET"])
@login_required
def view_return_request(return_id):
    return_request = ReturnRequest.query.get_or_404(return_id)
    return render_template('view-return-request.html', return_request=return_request)

@app.route('/delete-return/<int:return_id>', methods=['POST'])
def delete_return(return_id):
    print(f"Attempting to delete return with ID: {return_id}")
    return_request = ReturnRequest.query.get_or_404(return_id)
    order_detail = return_request.order_detail
    order = order_detail.order_relation if order_detail else None
    try:
        if order_detail and order:
            order_detail.odstarus = "Processing"  
            order.status = 'Delivered'
        db.session.delete(return_request)
        db.session.commit()
        flash("Return request deleted successfully.", "success")
    except Exception as e:
        db.session.rollback() 
        flash(f"Error deleting return request: {str(e)}", "danger")
    return redirect(url_for('returns'))

@app.route('/inspect-return/<int:return_id>', methods=['GET', 'POST'])
def inspect_return(return_id):
    return_request = ReturnRequest.query.get_or_404(return_id)    
    if request.method == 'POST':
        # Lấy điều kiện từ form
        condition = request.form.get('condition')        
        if condition not in ['Good', 'Damaged']:
            flash("Invalid product condition.", "danger")
            return redirect(url_for('view_returns'))
        return_request.return_status = "Processing"
        return_request.condition = condition
        db.session.commit() 
        flash("Return inspected successfully.", "success")
        return redirect(url_for('create_return'))  
    return render_template('return_form.html', return_request=return_request)





@app.route('/check-material-existence')
def check_material_existence():
    material_name = request.args.get('material_name')
    existing_material = Import.query.filter_by(material_name=material_name).first()
    if existing_material:
        return jsonify({'exists': True})
    return jsonify({'exists': False})



# @app.route("/dub-products/", methods=["POST"])
# def getProductDuplicate():
#     if request.method == "POST":
#         product_name = request.form["product_name"]
#         products = Product.query.filter(Product.pro_name == product_name).all()

#         if products:
#             return jsonify({"output": False})  # Name exists
#         else:
#             return jsonify({"output": True})  # Name is unique

















if __name__ == "__main__":
    app.run(debug=True)
    