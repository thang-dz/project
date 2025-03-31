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

class Import(db.Model):
    __tablename__ = 'imports'
    import_id = db.Column(db.Integer, primary_key=True)
    
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

    def __repr__(self):
        return f"<Batch #{self.batch_id} - OrderDetail #{self.order_detail_id}>"
    
    def is_complete(self):       
        return self.quantity_in_production == self.quantity_completed


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

@app.route('/classify-material/<int:inventory_id>', methods=["POST"])
def classify_material(inventory_id):
    inventory_item = Inventory.query.get_or_404(inventory_id)
    category = request.form.get('category')
    inventory_item.category = category
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


@app.route('/update-inventory/<int:inventory_id>', methods=["POST", "GET"])
def update_inventory(inventory_id):
    inventory = Inventory.query.get_or_404(inventory_id)

    if request.method == "POST":
        quantity_removed = int(request.form.get("quantity_removed"))

        if quantity_removed > inventory.quantity:
            flash("Cannot remove more than available stock.", "danger")
            return redirect(url_for('update_inventory', inventory_id=inventory_id))

        inventory.quantity -= quantity_removed
        inventory.transaction_type = "Removal"
        db.session.commit()

        flash(f"{quantity_removed} units removed from inventory.", "success")
        return redirect(url_for('view_inventory'))

    return render_template("update-inventory.html", inventory=inventory)

@app.route('/add-import/', methods=["GET", "POST"])
def add_import():
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
            sup_address=sup_address,
            status="Wait"
        
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
def update_import_status(import_id):
    import_record = Import.query.get_or_404(import_id)

    # Kiểm tra xem trạng thái có phải là "Wait"
    if import_record.status == "Supplied":
        import_record.status = "Success"

        # Thêm vào inventory
        new_inventory_item = Inventory(
            product_name=import_record.material_name,
            quantity=import_record.quantity_in_stock,
            transaction_type="Addition",  # Thêm vào kho
            import_id=import_record.import_id
        )

        try:
            # Cập nhật status của Import và thêm vào Inventory
            db.session.add(new_inventory_item)
            db.session.commit()
            flash("Import status updated and material added to inventory.", "success")
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
        import_record.material_name = request.form['material_name']
        import_record.material_description = request.form.get('material_description', '')
        import_record.quantity_in_stock = int(request.form.get('quantity_in_stock', 0))
        import_record.reorder_level = int(request.form.get('reorder_level', 10))

        import_record.sup_name = request.form['sup_name']
        import_record.sup_contact_info = request.form['sup_contact_info']
        import_record.sup_address = request.form['sup_address']

        try:
            db.session.commit()
            flash("Import updated successfully!", "success")
            return redirect(url_for('view_import'))
        except Exception as e:
            db.session.rollback()
            flash(f"Error updating import: {str(e)}", "danger")

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

        # Create new order record
        new_order = Order(
            cus_name=cus_name,
            cus_contact=cus_contact,
            cus_address=cus_address,
            price=price,
            order_date=order_date
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
    return "${:,.2f}".format(value)


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



@app.route('/create_purchase_request/<int:import_id>', methods=["GET", "POST"])
def create_purchase_request(import_id):
    # Fetch the import record using import_id
    import_request = Import.query.get_or_404(import_id)

    # Check if stock is below reorder level
    if import_request.quantity_in_stock < import_request.reorder_level:
        if request.method == "POST":
            # Get the quantity to order from form input
            quantity_to_order = request.form.get("quantity", type=int)
            
            # Ensure quantity is valid
            if quantity_to_order and quantity_to_order > 0:
                try:
                    # Create a new purchase request
                    new_purchase_request = PurchaseRequest(
                        import_id=import_request.import_id,
                        quantity_requested=quantity_to_order,
                        transaction_date=datetime.utcnow()
                    )
                    db.session.add(new_purchase_request)
                    db.session.commit()

                    # Update the stock in inventory (Optional: If stock is replenished)
                    import_request.quantity_in_stock += quantity_to_order
                    db.session.commit()

                    flash("Purchase request created and stock updated successfully.", "success")
                    return redirect(url_for('view_inventory'))  # Redirect to inventory view

                except Exception as e:
                    db.session.rollback()  # Rollback on error
                    flash(f"An error occurred: {str(e)}", "danger")
            else:
                flash("Invalid quantity! Please enter a valid quantity.", "danger")
        
        return render_template("create_purchase_request.html", import_request=import_request)

    flash("Stock level is sufficient. No purchase request needed.", "info")
    return redirect(url_for('view_inventory'))


@app.route('/add-product-batch/', methods=["GET", "POST"])
def add_product_batch():
    order_details = OrderDetail.query.all()

    if request.method == "POST":
        order_detail_id = request.form['order_detail_id']
        batch_number = request.form['batch_number']
        category = request.form['category']

        # Check if batch number already exists
        existing_batch = ProductBatch.query.filter_by(batch_number=batch_number).first()
        if existing_batch:
            flash("Batch number already exists.", 'danger')
            return redirect(url_for('add_product_batch'))

        # Create a new product batch
        new_batch = ProductBatch(
            order_detail_id=order_detail_id,
            batch_number=batch_number,
            category=category
        )

        try:
            db.session.add(new_batch)
            db.session.commit()
            flash("Product batch added successfully.", 'success')
            return redirect(url_for('view_product_batches'))
        except Exception as e:
            db.session.rollback()
            flash(f"Error: {str(e)}", 'danger')

    return render_template('add_product_batch.html', order_details=order_details)

@app.route('/view-product-batches/', methods=["GET"])
def view_product_batches():
    product_batches = ProductBatch.query.all()
    return render_template('view_product_batches.html', product_batches=product_batches)

@app.route('/manufacturing-management/', methods=["GET", "POST"])
def manufacturing_management():
    if request.method == "POST":
        # Retrieve form data
        batch_id = request.form['batch_id']
        order_id = request.form['order_id']
        product_name = request.form['product_name']
        material = request.form['material']
        product_quantity = int(request.form['product_quantity'])  # Assuming this is the quantity entered by the user

        # Get the product batch
        product_batch = ProductBatch.query.get(batch_id)
        if not product_batch:
            flash("Product batch not found.", 'danger')
            return redirect(url_for('manufacturing_management'))

        # Ensure the batch is complete before proceeding
        if not product_batch.is_complete():
            flash("Cannot proceed with incomplete materials.", 'danger')
            return redirect(url_for('manufacturing_management'))

        # Ensure the product batch contains the specified material
        if material not in product_batch.materials:
            flash("Material not found in the product batch.", 'danger')
            return redirect(url_for('manufacturing_management'))

        # Enforce valid quantity updates
        available_material_quantity = product_batch.materials[material]  # Assume we have a materials dict
        if product_quantity > available_material_quantity:
            flash("Invalid quantity: exceeds available stock for this material.", "danger")
            return redirect(url_for('manufacturing_management'))

        # Update the product batch and reduce material quantity
        product_batch.materials[material] -= product_quantity  # Deduct the quantity from material stock
        product_batch.quantity_in_production -= product_quantity  # Deduct from production quantity (example)

        # If all quantity in production is used, update status to 'Completed'
        if product_batch.quantity_in_production == 0:
            product_batch.manufacturing_status = 'Completed'

        # Check if this product already exists in OrderDetail with the same order_id and product_name
        existing_order_detail = OrderDetail.query.filter_by(order_id=order_id, product_name=product_name).first()

        if existing_order_detail:
            # If the product already exists, update the quantity
            existing_order_detail.product_quantity += product_quantity
        else:
            # Otherwise, create a new order detail entry
            order_detail = OrderDetail(
                order_id=order_id,
                product_name=product_name,
                product_quantity=product_quantity
            )
            db.session.add(order_detail)

        # Commit changes to the database
        try:
            db.session.commit()
            flash(f"Manufacturing status updated to {product_batch.manufacturing_status}.", 'success')
        except Exception as e:
            db.session.rollback()
            flash(f"Error: {str(e)}", 'danger')

        # Redirect to the product batches view
        return redirect(url_for('view_product_batches'))

    # For GET requests, render the manufacturing management page
    return render_template('manufacturing_management.html')



def generate_tracking_code():
    length = 10
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

@app.route('/create-shipping-order/<int:order_id>', methods=["GET", "POST"])
def create_shipping_order(order_id):
    # Fetch the order from the database
    order = Order.query.get_or_404(order_id)
    
    # Check if the order has already been shipped or has a shipping status other than "Pending"
    # Access the first shipping record if it exists
    if order.shipping_details:
        shipping_record = order.shipping_details[0]  # Get the first shipping record
        if shipping_record.shipping_status != "Pending":
            flash("This order has already been shipped or is not in pending status. It cannot be shipped again.", "danger")
            return redirect(url_for('view_shipping', shipping_id=shipping_record.shipping_id))

    if request.method == "POST":
        provider = request.form['provider']
        shipping_cost = request.form.get('shipping_cost', type=float)

        # Validate shipping cost
        if shipping_cost is None or shipping_cost <= 0:
            flash("Shipping cost must be a positive value.", "danger")
            return redirect(url_for('create_shipping_order', order_id=order_id))

        # Generate a unique tracking code
        tracking_code = generate_tracking_code()

        # Check if the tracking code already exists, if it does, regenerate it
        while Shipping.query.filter_by(tracking_code=tracking_code).first():
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
    
    # Render the template and pass the order object
    return render_template('create_shipping_order.html', order=order)

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




@app.route("/dub-material/", methods=["POST"])
def getMaterialDuplicate():
    if request.method == "POST":
        material_name = request.form["material_name"]
        materials = Import.query.filter(Import.material_name == material_name).all()

        if materials:
            return jsonify({"output": False})  # Name exists
        else:
            return jsonify({"output": True})  # Name is unique





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
    