import random
import string
from flask import Flask, jsonify, render_template, request, session, url_for, redirect, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from flask_wtf import FlaskForm
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

    def __repr__(self):
        return f'<Import {self.import_id}>'

class Order(db.Model):
    __tablename__ = 'orders'
    order_id = db.Column(db.Integer, primary_key=True)
    cus_name = db.Column(db.String(255), nullable=False)  # Customer Name
    cus_contact = db.Column(db.String(255), nullable=False)  # Customer Contact
    cus_address = db.Column(db.String(255), nullable=False)  # Customer Address
    order_date = db.Column(db.DateTime, default=datetime.utcnow)
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
    transaction_date = db.Column(db.DateTime, default=datetime.utcnow)  # Date of transaction

    import_id = db.Column(db.Integer, db.ForeignKey('imports.import_id'), nullable=False)  # Foreign Key to Import (raw material)

    # Relationship to Import (Material)
    import_data = db.relationship('Import', backref='inventory_records', lazy=True)

    def __repr__(self):
        return f'<Inventory {self.product_name}>'

class DepositConfirm(db.Model):
    __tablename__ = 'deposit_confirm'
    id = db.Column(db.Integer, primary_key=True)  # Khoá chính của bảng
    order_id = db.Column(db.Integer, db.ForeignKey('orders.order_id'), nullable=False)  # Mã đơn hàng (khóa ngoại)
    deposit_amount = db.Column(db.Numeric(10, 2), nullable=False)  # Số tiền gửi
    transaction_date = db.Column(db.DateTime, default=datetime.utcnow)  # Ngày giao dịch

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
    transaction_date = db.Column(db.DateTime, default=datetime.utcnow)

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
    shipment_time = db.Column(db.DateTime, default=datetime.utcnow)
    order = db.relationship('Order', backref='shipping_details')

    def __repr__(self):
        return f"<Shipping {self.shipping_id} - Order {self.order_id}>"





class PurchaseRequest(db.Model):
    __tablename__      = 'purchase_request'
    id                 = db.Column(db.Integer, primary_key=True)
    import_id           = db.Column(db.Integer, db.ForeignKey('imports.import_id'))
    quantity_requested = db.Column(db.Integer, nullable=False)
    transaction_date   = db.Column(db.DateTime, default=datetime.utcnow)

    import_request = db.relationship('Import', backref='order_request', lazy=True)

    def __repr__(self):
        return f'<PurchaseRequest {self.id}>'


# class Payment(db.Model):

#     __tablename__ = 'payment'
#     payment_id    = db.Column(db.Integer, primary_key=True)
#     order_id      = db.Column(db.Integer, db.ForeignKey('order.order_id'))
#     amount        = db.Column(db.Numeric(10, 2), nullable=False)
#     status        = db.Column(db.String(50), default='Pending')
#     payment_date  = db.Column(db.DateTime, default=datetime.utcnow)
#     order         = db.relationship('Order', backref='payments')

#     def __repr__(self):
#         return '<Payment %r>' % self.payment_id
# class Shipping(db.Model):

    # __tablename__ = 'shipping'
    # shipping_id   = db.Column(db.Integer, primary_key=True)
    # order_id      = db.Column(db.Integer, db.ForeignKey('order.order_id'))
    # provider      = db.Column(db.String(255))
    # tracking_code = db.Column(db.String(255), unique=True)
    # status        = db.Column(db.String(50), default='Pending')
    # order         = db.relationship('Order', backref='shipping')

    # def __repr__(self):
    #     return '<Shipping %r>' % self.shipping_id

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
    imports = Import.query.all()
    return render_template("inventory.html", inventory=inventory, imports=imports)
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

    return render_template("add-import.html")

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
            order_date = datetime.utcnow()
        else:
            order_date = datetime.strptime(order_date_str, '%Y-%m-%dT%H:%M')

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

        # Retrieve product information
        product_name = request.form.get("product_name")
        product_price = request.form.get("product_price")
        quantity = request.form.get("quantity")
        import_id = request.form.get("import_id")

        # Ensure all product details are present
        if not product_name or not product_price or not quantity or not import_id:
            flash("All product fields are required.", "danger")
            return redirect(url_for('add_order'))

        # Process product details
        product_price = float(product_price)
        quantity = int(quantity)

        # Add order details
        order_detail = OrderDetail(
            order_id=new_order.order_id,
            product_name=product_name,
            product_price=product_price,
            quantity=quantity,
            import_id=import_id,
        )
        db.session.add(order_detail)

        # Adjust inventory based on the import
        import_record = Import.query.get(import_id)
        inventory_record = Inventory.query.filter_by(product_name=import_record.material_name).first()
        if inventory_record:
            inventory_record.quantity += quantity
        else:
            new_inventory = Inventory(
                product_name=product_name,
                quantity=quantity,
                transaction_type="Addition",
                import_id=import_record.import_id
            )
            db.session.add(new_inventory)

        db.session.commit()
        flash("Order added successfully and products moved to inventory!", "success")
        return redirect("/order/")

    # Fetch imports to populate select options
    imports = Import.query.all()
    return render_template('add-order.html', imports=imports)
@app.template_filter('format_price')
def format_price(value):
    return "${:,.2f}".format(value)


@app.route('/order/', methods=["GET", "POST"])
def view_order():
    orders = Order.query.all()
    imports = Import.query.all()
    return render_template("order.html", orders=orders, imports=imports)

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
            flash(f"Deposit is insufficient. The required amount is {order.price}, but you entered {deposit_amount}. Please try again.", "danger")
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


# @app.route('/inventory/', methods=["GET"])
# def inventory():
#     # Lấy tất cả các sản phẩm, giao dịch kho và vật liệu
#     # products = Product.query.all()  # Lấy tất cả sản phẩm
#     transactions = Inventory.query.all()  # Lấy tất cả giao dịch kho
#     materials = Material.query.all()  # Lấy tất cả vật liệu
#     return render_template('inventory.html',  transactions=transactions, materials=materials)
# @app.route("/delete-transaction/<int:transaction_id>", methods=["GET", "POST"])
# def delete_transaction(transaction_id):
#     transaction = Inventory.query.get_or_404(transaction_id)
    
#     try:
#         db.session.delete(transaction)  # Xóa giao dịch kho
#         db.session.commit()  # Commit thay đổi vào cơ sở dữ liệu
#         flash("Transaction deleted successfully!", "success")
#     except Exception as e:
#         db.session.rollback()  # Rollback nếu có lỗi
#         flash(f"Error deleting transaction: {str(e)}", "danger")
    
#     return redirect(url_for('inventory'))  # Quay lại trang Inventory
# @app.route('/create-purchase-request/<int:material_id>', methods=["GET", "POST"])
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
        manufacturing_status = request.form['manufacturing_status']
        product_condition = request.form['product_condition']
        defect_reason = request.form.get('defect_reason', '')
        quantity_to_update = int(request.form.get('quantity_to_update', 0))  # Assuming you have quantity to update

        # Get the product batch
        product_batch = ProductBatch.query.get(batch_id)
        if not product_batch:
            flash("Product batch not found.", 'danger')
            return redirect(url_for('manufacturing_management'))

        # Prevent processing of incomplete product batches
        if not product_batch.is_complete():  # Using the new method
            flash("Cannot proceed with incomplete materials.", 'danger')
            return redirect(url_for('manufacturing_management'))

        # Workflow validation for manufacturing status transitions
        valid_transitions = {
            'In Production': ['Completed'],
            'Completed': ['Ready for Shipping']
        }

        # Check if the status transition is valid
        if manufacturing_status != product_batch.manufacturing_status:
            if product_batch.manufacturing_status not in valid_transitions or manufacturing_status not in valid_transitions[product_batch.manufacturing_status]:
                flash("Invalid status transition!", "danger")
                return redirect(url_for('manufacturing_management'))

        # Ensure defect reason is provided if the condition is 'Defective'
        if product_condition == 'Defective' and not defect_reason:
            flash("Please provide a reason for the defect.", 'danger')
            return redirect(url_for('manufacturing_management'))

        # Enforce valid product quantity updates (assuming you have quantity data)
        available_stock = product_batch.quantity_in_production  # Example: assuming this holds the available stock
        if quantity_to_update > available_stock:
            flash("Invalid quantity: exceeds available stock.", "danger")
            return redirect(url_for('manufacturing_management'))

        # Update the manufacturing status and product condition
        product_batch.manufacturing_status = manufacturing_status
        product_batch.product_condition = product_condition
        product_batch.defect_reason = defect_reason if product_condition == 'Defective' else None

        # Update quantities based on manufacturing status
        if manufacturing_status == 'Completed':
            product_batch.quantity_completed += quantity_to_update
        elif manufacturing_status == 'Ready for Shipping':
            product_batch.quantity_ready_for_shipping += quantity_to_update

        # Commit changes to the database
        try:
            db.session.commit()
            flash(f"Manufacturing status updated to {manufacturing_status}.", 'success')
        except Exception as e:
            db.session.rollback()
            flash(f"Error: {str(e)}", 'danger')

        # Redirect to the product batches view
        return redirect(url_for('view_product_batches'))

    # For GET requests, render the manufacturing management page
    return render_template('manufacturing_management.html')


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

        # Create shipping order
        shipping = Shipping(
            order_id=order_id,
            provider=provider,
            tracking_code="GENERATED_CODE",  # Replace with actual tracking code logic
            shipping_cost=shipping_cost,
            shipping_status="Pending"
        )

        try:
            db.session.add(shipping)
            db.session.commit()
            flash(f"Shipping order created for Order #{order_id}.", 'success')
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
    shipping = Shipping.query.get_or_404(shipping_id)
    return render_template('view_shipping.html', shipping=shipping)





# @app.route('/shippings/<int:shipping_id>', methods=["GET"])
# def view_shipping(shipping_id):
#     shipping = Shipping.query.get_or_404(shipping_id)
#     return render_template('view_shipping.html', shipping=shipping)
# @app.route('/cancel-shipping/<int:shipping_id>', methods=["POST"])
# def cancel_shipping(shipping_id):
#     shipping = Shipping.query.get_or_404(shipping_id)  # Lấy thông tin đơn vận chuyển
#     try:
#         db.session.delete(shipping)  # Xóa đơn vận chuyển
#         db.session.commit()
#         flash("Shipping process has been successfully canceled.", "success")
#     except Exception as e:
#         db.session.rollback()
#         flash(f"Failed to cancel shipping. Please try again. Error: {str(e)}", "danger")

#     return redirect(url_for('shipping'))  # Quay lại trang quản lý vận chuyển









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
    