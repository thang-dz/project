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
from datetime import datetime


app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret-key-goes-here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///inventory.db'
db = SQLAlchemy(app)
# login_manager = LoginManager()
# login_manager.init_app(app)
# login_manager.login_view = "login"

# @login_manager.user_loader
# def load_user(user_id):
#     return User.query.get(int(user_id))

# # Bảng Người dùng
# class User(UserMixin, db.Model):
#     id       = db.Column(db.Integer, primary_key=True)
#     email    = db.Column(db.String(100), unique=True, nullable=False)
#     password = db.Column(db.String(100), nullable=False)
#     name     = db.Column(db.String(100), nullable=False)


# Vietnam Time (UTC +7)
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
    reorder_level = db.Column(db.Integer, default=10)
    
    # Supplier info
    sup_name = db.Column(db.String(255), nullable=False)
    sup_contact_info = db.Column(db.String(255), nullable=False)
    sup_address = db.Column(db.String(255), nullable=False)
    
    status = db.Column(db.String(50), default="Supplied")
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

    order_details = db.relationship('OrderDetail', backref='order_relation', lazy=True)

    def __repr__(self):
        return f'<Order {self.order_id}>'

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
    import_id = db.Column(db.Integer, db.ForeignKey('imports.import_id'))  # Import relation

    # Relationship to Import
    import_record = db.relationship('Import', backref='order_details', lazy=True)
    

    def __repr__(self):
        return f'<OrderDetail {self.orderdetail_id}>'


class ProductBatch(db.Model):
    __tablename__ = 'product_batches'
    batch_id = db.Column(db.Integer, primary_key=True)
    batch_number = db.Column(db.String(50), nullable=False)
    category = db.Column(db.String(100))

    # Liên kết với OrderDetail để lấy thông tin sản phẩm
    order_detail_id = db.Column(db.Integer, db.ForeignKey('order_details.order_detail_id'))
    order_detail = db.relationship('OrderDetail', backref='product_batches')

    quantity_in_production = db.Column(db.Integer, default=0)
    quantity_completed = db.Column(db.Integer, default=0)
    quantity_ready_for_shipping = db.Column(db.Integer, default=0)

    manufacturing_status = db.Column(db.String(50), default='In Production')
    product_condition = db.Column(db.String(50), nullable=True)
    defect_reason = db.Column(db.String(255), nullable=True)
    transaction_date = db.Column(db.DateTime, default=vietnam_now)
    quantity_to_update=db.Column(db.Integer, default=0)

    inventory = db.relationship('Inventory', secondary=product_batch_materials, backref='product_batches')
    

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
    status = db.Column(db.String(50), default='Pending')  # Trạng thái mặc định là "Pending"
    
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
    shipping_status = db.Column(db.String(50), default='Pending')  # Status: Pending, Shipped, Delivered
    shipment_time = db.Column(db.DateTime, default=vietnam_now)
    order = db.relationship('Order', backref='shipping_details')

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


# # Form Đăng nhập
# class LoginForm(FlaskForm):
#     email = StringField('Email', validators=[DataRequired(), Email()])
#     password = PasswordField('Password', validators=[DataRequired()])
#     submit = SubmitField('Login')

# Khởi tạo Database
with app.app_context():
    # db.drop_all() 
    db.create_all()

# @app.route('/')
# def home():
#     return render_template("index.html")

# @app.route('/login', methods=['GET', 'POST'])
# def login():
#     form = LoginForm()
#     if form.validate_on_submit():
#         user = User.query.filter_by(email=form.email.data).first()
#         if user and check_password_hash(user.password, form.password.data):
#             login_user(user)
#             return redirect(url_for('home'))
#         else:
#             flash('Invalid email or password', 'danger')
#     return render_template('login.html', form=form)
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/inventory/')
def view_inventory():
    inventory = Inventory.query.all()
    low_stock_items = [item for item in inventory if item.quantity <= item.import_data.reorder_level]
    imports = Import.query.all()
    return render_template("inventory.html", inventory=inventory, imports=imports,low_stock_items=low_stock_items )

@app.route('/classify-warehouse/<int:inventory_id>', methods=["POST"])
def classify_warehouse(inventory_id):
    inventory_item = Inventory.query.get_or_404(inventory_id)
    warehouse = request.form.get('warehouse')  # Lấy warehouse từ form
    inventory_item.warehouse = warehouse  # Cập nhật warehouse cho item
    db.session.commit()  # Lưu thay đổi vào cơ sở dữ liệu
    flash(f"Material {inventory_item.product_name} classified as {warehouse}.", "success")
    return redirect(url_for('view_inventory'))


@app.route('/classify-material/<int:inventory_id>', methods=["POST"])
def classify_material(inventory_id):
    inventory_item = Inventory.query.get_or_404(inventory_id)
    category = request.form.get('category')
    inventory_item.category = category  # Update the category in the database
    db.session.commit()
    flash(f"Material {inventory_item.product_name} classified as {category}.", "success")
    return redirect(url_for('view_inventory'))


@app.route('/delete-inventory/<int:inventory_id>', methods=["POST"])
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
def create_purchase_request(import_id):
    import_request = Import.query.get_or_404(import_id)
    inventory=Inventory.query.get_or_404(import_id)

    # Kiểm tra nếu số lượng còn thiếu và nhỏ hơn reorder level
    if inventory.quantity < import_request.reorder_level:
        # Tính toán số lượng cần nhập
        quantity_needed = import_request.reorder_level - inventory.quantity

        # Chuyển hướng đến trang add-import với các thông tin cần thiết đã được điền sẵn
        return redirect(url_for('add_imports', 
                                material_name=import_request.material_name, 
                                material_description=import_request.material_description,
                                reorder_level=import_request.reorder_level,
                                quantity_needed=quantity_needed,
                                sup_name=import_request.sup_name,
                                sup_contact_info=import_request.sup_contact_info,
                                sup_address=import_request.sup_address   ))

    flash("Stock level is sufficient. No purchase request needed.", "info")
    return redirect(url_for('view_inventory'))

@app.route('/add-imports/', methods=["GET", "POST"])
def add_imports():
    if request.method == "POST":
        material_name = request.form["material_name"]

        # Kiểm tra xem material_name đã tồn tại trong cơ sở dữ liệu chưa
        # existing_material = Import.query.filter_by(material_name=material_name).first()
        # if existing_material:
        #     flash("Material name already exists. Please choose a different name.", "danger")
        #     return render_template("add-imports.html")

        material_description = request.form.get("material_description", "")
        quantity_in_stock = int(request.form.get("quantity_in_stock", 0))
        reorder_level = int(request.form.get("reorder_level", 10))
        
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
            status="Supplied"
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
    reorder_level = request.args.get('reorder_level', type=int, default=10)
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
def add_import():
    if request.method == "POST":
        material_name = request.form["material_name"]
        
        # Kiểm tra xem material_name đã tồn tại trong cơ sở dữ liệu chưa
        # existing_material = Import.query.filter_by(material_name=material_name).first()
        # if existing_material:
        #     flash("Material name already exists. Please choose a different name.", "danger")
        #     return render_template("add-import.html")

        material_description = request.form.get("material_description", "")
        quantity_in_stock = int(request.form.get("quantity_in_stock", 0))
        reorder_level = int(request.form.get("reorder_level", 10))
        
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
            status="Supplied"
        )

        try:
            db.session.add(new_import)
            db.session.commit()
            flash("Import added successfully!", "success")
            return redirect(url_for('view_import'))  # Redirect to the page showing imports
        except Exception as e:
            db.session.rollback()
            flash(f"Error adding import: {str(e)}", "danger")

    return render_template("add-import.html")  # Render the form when GET request


@app.route('/update-import-status/<int:import_id>', methods=["POST"])
def update_import_status(import_id):
    import_record = Import.query.get_or_404(import_id)

    # Kiểm tra trạng thái của Import
    if import_record.status == "Supplied":
        import_record.status = "Success"

        # Check if the material already exists in the inventory
        existing_inventory_item = Inventory.query.filter_by(product_name=import_record.material_name).first()

        if existing_inventory_item:
            # If the material exists, update the quantity in inventory
            existing_inventory_item.quantity += import_record.quantity_in_stock
            flash(f"Material {import_record.material_name} quantity updated in inventory.", "success")
        else:
            # If the material doesn't exist, create a new inventory item
            new_inventory_item = Inventory(
                product_name=import_record.material_name,
                quantity=import_record.quantity_in_stock,
                transaction_type="Addition",  # Thêm vào kho
                import_id=import_record.import_id,
            )
            db.session.add(new_inventory_item)
            flash(f"New material {import_record.material_name} added to inventory.", "success")

        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            flash(f"Error updating status or adding to inventory: {str(e)}", "danger")

    else:
        flash("The import is already marked as 'Success'.", "warning")

    return redirect(url_for('view_import'))


@app.route('/update-import/<int:import_id>', methods=["POST", "GET"])
def update_import(import_id):
    import_record = Import.query.get_or_404(import_id)

    if request.method == "POST":
        # Cập nhật thông tin import
        import_record.material_name = request.form['material_name']
        import_record.material_description = request.form.get('material_description', '')
        import_record.quantity_in_stock = int(request.form.get('quantity_in_stock', 0))
        import_record.reorder_level = int(request.form.get('reorder_level', 10))

        import_record.sup_name = request.form['sup_name']
        import_record.sup_contact_info = request.form['sup_contact_info']
        import_record.sup_address = request.form['sup_address']

        # Cập nhật số lượng trong Inventory nếu tồn tại
        inventory_item = Inventory.query.filter_by(import_id=import_record.import_id).first()
        if inventory_item:
            inventory_item.quantity = import_record.quantity_in_stock  # Cập nhật lại số lượng
            try:
                db.session.commit()
                flash("Import updated successfully and inventory updated!", "success")
                return redirect(url_for('view_import'))
            except Exception as e:
                db.session.rollback()
                flash(f"Error updating import or inventory: {str(e)}", "danger")
        else:
            flash("Inventory item not found for this import.", "danger")
           
            new_inventory_item = Inventory(
                product_name=import_record.material_name,
                quantity=import_record.quantity_in_stock,
                transaction_type="Addition",  # Thêm vào kho
                import_id=import_record.import_id,
            )
            db.session.add(new_inventory_item)
            db.session.commit()

    return render_template("update-import.html", import_record=import_record)



@app.route('/delete-import/<int:import_id>', methods=["POST"])
def delete_import(import_id):
    import_record = Import.query.get_or_404(import_id)

    try:
        db.session.delete(import_record)
        db.session.commit()
        flash("Import deleted successfully!", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error deleting import: {str(e)}", "danger")

    return redirect(url_for('view_import'))

@app.route('/import/', methods=["GET", "POST"])
def view_import():
    if request.method == "POST":
        material_name = request.form["material_name"]
        material_description = request.form.get("material_description", "")
        quantity_in_stock = int(request.form.get("quantity_in_stock", 0))
        reorder_level = int(request.form.get("reorder_level", 10))
        
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
def add_order():
    if request.method == "POST":
        # Retrieve customer information
        cus_name = request.form["cus_name"]
        cus_contact = request.form.get("cus_contact", "")
        cus_address = request.form.get("cus_address", "")
        
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
            deposit_amount=deposit_amount  # Store deposit amount in the order record
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

        flash("Order added successfully with multiple products!", "success")
        return redirect("/order/")

    return render_template('add-order.html')


@app.template_filter('format_price')
def format_price(value):
    try:
        # Format the price as currency (e.g., 1,000,000.00)
        return "{:,.2f}".format(value)
    except (ValueError, TypeError):
        return value


@app.route('/order/', methods=["GET", "POST"])
def view_order():
    orders = Order.query.all()    
    return render_template("order.html", orders=orders)

@app.route("/order-detail/<int:order_id>")
def order_detail(order_id):
    order = Order.query.get_or_404(order_id)
    return render_template("order-detail.html", order=order)



# Route để xem chi tiết đơn hàng
@app.route("/update-order/<int:order_id>", methods=["POST", "GET"])
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


# Route to delete an order
@app.route("/delete-order/<int:order_id>", methods=["GET", "POST"])
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



@app.route('/deposit-confirm/', methods=["POST", "GET"])
def deposit_confirm():
    if request.method == "POST":
        order_id = request.form.get("order_id")
        deposit_amount = request.form.get("deposit_amount", type=float)

        # Kiểm tra mã đơn hàng hợp lệ
        order = Order.query.filter_by(order_id=order_id).first()
        if not order:
            flash("Invalid order ID. Please try again.", "danger")
            return redirect(url_for('deposit_confirm'))

        # Kiểm tra số tiền gửi có đủ không
        if deposit_amount < order.price:
            flash(f"Deposit is insufficient. ", "danger")
            return redirect(url_for('deposit_confirm'))

        # Thêm giao dịch gửi tiền vào cơ sở dữ liệu
        deposit_confirm = DepositConfirm(
            order_id=order.order_id,
            deposit_amount=deposit_amount,
            transaction_date=datetime.utcnow()
        )
        db.session.add(deposit_confirm)
        db.session.commit()

        flash("Deposit recorded successfully.", "success")
        return redirect(url_for('deposit_confirm', order_id=order.order_id))  # Redirect to order details page

    return render_template("deposit_confirm.html")



@app.route('/add-product-batch/', methods=["GET", "POST"])
def add_product_batch():
    order_details = OrderDetail.query.all()
    inventory = Inventory.query.all()

    if request.method == "POST":
        order_detail_id = request.form['order_detail_id']
        batch_number = request.form['batch_number']
        category = request.form['category']
        material_ids = request.form.getlist('material_ids')  # List of material IDs

        # Check if the batch number already exists for the same order_detail_id
        existing_batch = ProductBatch.query.filter_by(order_detail_id=order_detail_id, batch_number=batch_number).first()
        if existing_batch:
            flash("Batch number already exists for this order.", 'danger')
            return redirect(url_for('add_product_batch'))

        # Create a new product batch
        new_batch = ProductBatch(
            order_detail_id=order_detail_id,
            batch_number=batch_number,
            category=category
        )

        # Link materials to the batch (many-to-many relationship)
        for material_id in material_ids:
            import_data = Inventory.query.get(material_id)
            if import_data:
                new_batch.inventory.append(import_data)  # Use the `imports` relationship

        try:
            db.session.add(new_batch)
            db.session.commit()
            flash("Product batch added successfully.", 'success')
            return redirect(url_for('view_product_batches'))
        except Exception as e:
            db.session.rollback()
            flash(f"Error: {str(e)}", 'danger')

    return render_template('add_product_batch.html', order_details=order_details, inventory=inventory)


@app.route('/delete-product-batch/<int:batch_id>', methods=["POST"])
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
def view_product_batches():
    product_batches = ProductBatch.query.all()
    return render_template('view_product_batches.html', product_batches=product_batches)

@app.route('/manufacturing-management/', methods=["GET", "POST"])
def manufacturing_management():
    if request.method == "POST":
        batch_id = request.form['batch_id']
        manufacturing_status = request.form['manufacturing_status']
        product_condition = request.form.get('product_condition', 'Good')  # Nếu không có, mặc định là 'Good'
        defect_reason = request.form.get('defect_reason', '')

        # Get the product batch
        product_batch = ProductBatch.query.get(batch_id)
        if not product_batch:
            flash("Product batch not found.", 'danger')
            return redirect(url_for('manufacturing_management'))

        # Validate status transition
        valid_transitions = {
            'In Production': ['Completed'],
            'Completed': ['Ready for Shipping']
        }

        if manufacturing_status != product_batch.manufacturing_status:
            if product_batch.manufacturing_status not in valid_transitions or manufacturing_status not in valid_transitions[product_batch.manufacturing_status]:
                flash("Invalid status transition!", "danger")
                return redirect(url_for('manufacturing_management'))

        # Update product batch status and condition
        product_batch.manufacturing_status = manufacturing_status
        product_batch.product_condition = product_condition
        product_batch.defect_reason = defect_reason if product_condition == 'Defective' else None

        # Commit changes to the database
        try:
            db.session.commit()
            flash("Manufacturing status updated successfully.", 'success')
        except Exception as e:
            db.session.rollback()
            flash(f"Error: {str(e)}", 'danger')

        # Move to ShippingQueue if product batch is "Ready for Shipping"
        if manufacturing_status == "Ready for Shipping":
            shipping_queue_item = ShippingQueue(
                order_id=product_batch.order_detail.order_id,
                batch_id=product_batch.batch_id,
                product_name=product_batch.order_detail.product_name,
                quantity=product_batch.quantity_completed,
                status="Pending"  # Initial status for shipping
            )
            db.session.add(shipping_queue_item)
            db.session.commit()

            flash(f"Product moved to shipping queue for Order #{product_batch.order_detail.order_id}", 'success')
            return redirect(url_for('shipping_queue_list'))  # Redirect to shipping queue list

        # Reload updated data
        product_batches = ProductBatch.query.all()
        inventories = Inventory.query.all()

        return render_template('manufacturing_management.html', product_batches=product_batches, inventories=inventories)

    # For GET requests, render the manufacturing management page with fresh data
    product_batches = ProductBatch.query.all()
    inventories = Inventory.query.all()
    return render_template('manufacturing_management.html', product_batches=product_batches, inventories=inventories)

@app.route('/update-quantity-produced/<int:batch_id>', methods=["GET", "POST"])
def update_quantity_produced(batch_id):
    product_batch = ProductBatch.query.get(batch_id)
    if not product_batch:
        flash("Product batch not found.", 'danger')
        return redirect(url_for('view_product_batches'))

    order_detail = product_batch.order_detail  # Order related to the batch

    if request.method == "POST":
        # Nhập số lượng sản phẩm đã sản xuất
        quantity_to_update = int(request.form.get('quantity_to_update', 0))  # Quantity produced for this batch

        # Cập nhật số lượng sản phẩm đã sản xuất cho batch
        product_batch.quantity_completed = quantity_to_update  # Update quantity_completed with the new value

        # Cập nhật số lượng trong kho (trừ số lượng tương ứng từ kho)
        for inventory_record in product_batch.inventory:  # Many-to-many relationship now
            if inventory_record.quantity >= quantity_to_update:
                # Trừ số lượng trong kho và bản ghi nhập
                inventory_record.quantity -= quantity_to_update

                try:
                    db.session.commit()
                    flash("Quantity produced updated successfully and inventory updated.", 'success')
                except Exception as e:
                    db.session.rollback()
                    flash(f"Error updating inventory: {str(e)}", 'danger')
                    return redirect(url_for('view_product_batches'))
            else:
                flash(f"Not enough stock in inventory for material: {inventory_record.product_name}.", 'danger')
                return redirect(url_for('view_product_batches'))

        # Tính tổng số sản phẩm đã sản xuất (tổng tất cả các batch)
        total_produced = sum(batch.quantity_completed for batch in order_detail.product_batches)

        # So sánh số lượng sản phẩm đã sản xuất với quantity trong order
        if total_produced >= order_detail.quantity:
            # Nếu số lượng sản phẩm đã sản xuất bằng hoặc lớn hơn số lượng yêu cầu, chuyển trạng thái thành "Completed"
            product_batch.manufacturing_status = "Completed"
            db.session.commit()
            flash("Complete Product! Manufacturing status set to 'Completed'.", 'success')

        # Now handle "Ready for Shipping"
        if total_produced >= order_detail.quantity:
            product_batch.manufacturing_status = "Ready for Shipping"
            db.session.commit()

            # Now move all the produced quantity (from all batches) to shipping queue
            total_quantity_for_shipping = sum(batch.quantity_completed for batch in order_detail.product_batches)

            shipping_queue_item = ShippingQueue(
                order_id=product_batch.order_detail.order_id,
                batch_id=product_batch.batch_id,
                product_name=product_batch.order_detail.product_name,
                quantity=total_quantity_for_shipping,
                status="Pending"  # Initial status for shipping
            )
            db.session.add(shipping_queue_item)
            db.session.commit()

            flash(f"Product moved to shipping queue for Order #{product_batch.order_detail.order_id}", 'success')

            return redirect(url_for('view_product_batches'))

        else:
            remaining_quantity = order_detail.quantity - total_produced
            flash(f"Remaining quantity to produce: {remaining_quantity}. Creating new batch...", 'warning')

            # Tạo một batch mới (batch number mới)
            new_batch_number = f"Batch-{batch_id+1}"  # Tạo batch number mới
            new_product_batch = ProductBatch(
                batch_number=new_batch_number,
                order_detail_id=order_detail.order_detail_id,
                manufacturing_status="In Production",  # Cập nhật trạng thái cho batch mới
                quantity_completed=0,  # Batch mới bắt đầu với quantity = 0
                transaction_date=vietnam_now()
            )
            db.session.add(new_product_batch)
            db.session.commit()

            # Cập nhật lại trạng thái sản xuất cho batch hiện tại nếu cần
            if total_produced + remaining_quantity >= order_detail.quantity:
                product_batch.manufacturing_status = "Completed"
                db.session.commit()
                flash("Complete Product with new batch!", 'success')

            return redirect(url_for('view_product_batches'))  # Quay lại trang quản lý sản xuất

    return render_template('view_product_batches.html', product_batch=product_batch)




@app.route('/shipping-queue/', methods=["GET"])
def shipping_queue_list():
    # Fetch all products that are ready for shipping (status "Pending")
    shipping_queue_items = ShippingQueue.query.filter_by(status="Pending").all()
    return render_template('shipping_queue.html', shipping_queue_items=shipping_queue_items)

@app.route('/create-shipping-order/<int:order_id>', methods=["GET", "POST"])
def create_shipping_order(order_id):
    # Fetch the order from the database
    order = Order.query.get_or_404(order_id)

    if request.method == "POST":
        provider = request.form['provider']
        shipping_cost = request.form.get('shipping_cost', type=float)

        # Validate shipping cost
        if shipping_cost is None or shipping_cost <= 0:
            flash("Shipping cost must be a positive value.", "danger")
            return redirect(url_for('create_shipping_order', order_id=order_id))

        # Generate a unique tracking code
        tracking_code = generate_tracking_code()

        # Create shipping order
        shipping = Shipping(
            order_id=order_id,
            provider=provider,
            tracking_code=tracking_code,
            shipping_cost=shipping_cost,
            shipping_status="Pending"
        )

        try:
            db.session.add(shipping)
            db.session.commit()
            flash(f"Shipping order created for Order #{order_id} with tracking code {tracking_code}.", 'success')
            return redirect(url_for('view_shipping', shipping_id=shipping.shipping_id))
        except Exception as e:
            db.session.rollback()
            flash(f"Error creating shipping order: {str(e)}", 'danger')
    
    return render_template('create_shipping_order.html', order=order)



def generate_tracking_code():
    length = 10
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

@app.route('/confirm-shipping-payment/<int:shipping_id>', methods=["POST", "GET"])
def confirm_shipping_payment(shipping_id):
    shipping = Shipping.query.get_or_404(shipping_id)
    order = Order.query.get_or_404(shipping.order_id)

    if request.method == "POST":
        try:
            payment_amount = float(request.form['payment_amount'])

            # Ensure the payment is sufficient for shipping
            if payment_amount < shipping.shipping_cost:
                flash("Insufficient payment for shipping.", "danger")
                return redirect(url_for('confirm_shipping_payment', shipping_id=shipping_id))

            # Update the shipping payment status and order status
            shipping.shipping_status = "Paid"
            order.shipping_status = "Shipped"  

            db.session.commit()

            flash("Shipping payment confirmed. Shipping marked as Paid.", "success")
            return redirect(url_for('view_shipping', shipping_id=shipping_id))

        except ValueError:
            flash("Invalid payment amount. Please enter a valid number.", "danger")
        except Exception as e:
            db.session.rollback()
            flash(f"Error during payment confirmation: {str(e)}", 'danger')

    return render_template('confirm_shipping_payment.html', shipping=shipping)

@app.route('/shipping-list/', methods=["GET"])
def shipping_list():
    # Phân trang danh sách vận chuyển (mỗi trang hiển thị 10 đơn vận chuyển)
    page = request.args.get('page', 1, type=int)
    shippings = Shipping.query.paginate(page=page, per_page=10)

    return render_template('shipping-list.html', shippings=shippings)

@app.route('/shipping/<int:shipping_id>', methods=["GET"])
def view_shipping(shipping_id):
    # Fetch the shipping object using the shipping_id
    shipping = Shipping.query.get_or_404(shipping_id)

    # If the shipping record exists, pass it to the template
    return render_template('view_shipping.html', shipping=shipping)



@app.route('/cancel-shipping/<int:shipping_id>', methods=["POST"])
def cancel_shipping(shipping_id):
    # Fetch the shipping order from the database
    shipping = Shipping.query.get_or_404(shipping_id)

    # Check if the shipping order is in "Pending" status
    if shipping.shipping_status != "Pending":
        flash("This shipping order cannot be canceled because it is either already shipped or canceled.", "danger")
        return redirect(url_for('view_shipping', shipping_id=shipping_id))

    try:
        # Update the shipping status to "Cancelled"
        shipping.shipping_status = "Cancelled"
        db.session.commit()
        flash("Shipping order has been successfully canceled.", "success")
    except Exception as e:
        db.session.rollback()  # Rollback in case of error
        flash(f"Error canceling shipping: {str(e)}", "danger")

    # Redirect to the shipping details page
    return redirect(url_for('view_shipping', shipping_id=shipping_id))

@app.route('/delete-shipping-queue/<int:shipping_queue_id>', methods=["POST"])
def delete_shipping_queue(shipping_queue_id):
    # Fetch the shipping queue item from the database
    shipping_queue_item = ShippingQueue.query.get_or_404(shipping_queue_id)

    try:
        # Delete the shipping queue item from the database
        db.session.delete(shipping_queue_item)
        db.session.commit()
        flash(f"Shipping queue item #{shipping_queue_id} deleted successfully.", "success")
    except Exception as e:
        db.session.rollback()  # Rollback if there's an error
        flash(f"Error deleting shipping queue item: {str(e)}", "danger")

    # Redirect back to the shipping queue list page after deletion
    return redirect(url_for('shipping_queue_list'))




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


# @app.route('/inventory', methods=['GET'])
# def get_inventory():
#     products = Product.query.all()
#     return jsonify([{ "id": p.id, "name": p.name, "stock": p.stock, "price": float(p.unit_price) } for p in products])

# @app.route('/add_product', methods=['POST'])
# def add_product():
#     data = request.get_json()
#     new_product = Product(name=data['name'], category=data.get('category', ''), unit_price=data['unit_price'], stock=data.get('stock', 0), supplier_id=data.get('supplier_id'))
#     db.session.add(new_product)
#     db.session.commit()
#     return jsonify({"message": "Product added successfully."})















if __name__ == "__main__":
    app.run(debug=True)
    