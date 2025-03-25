from flask import Flask, jsonify, render_template, request, url_for, redirect, flash
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


class ProductionBatch(db.Model):
    __tablename__ = 'production_batches'
    batch_id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.order_id'), nullable=False)
    week_number = db.Column(db.Integer, nullable=False)
    produced_quantity = db.Column(db.Integer, default=0)  # Quantity produced in this batch
    batch_date = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(50), default='In Production')  # Status of the batch

    order = db.relationship('Order', backref='production_batches', lazy=True)

    def __repr__(self):
        return f'<ProductionBatch {self.batch_id}, Week {self.week_number}, Status {self.status}>'


# Bảng Vận chuyển (Shipping)
# class Shipping(db.Model):
#     __tablename__ = 'shipping'
#     shipping_id = db.Column(db.Integer, primary_key=True)
#     order_id = db.Column(db.Integer, db.ForeignKey('order.order_id'))  # Corrected to reference order_id
#     provider = db.Column(db.String(255))
#     tracking_code = db.Column(db.String(255), unique=True)
#     status = db.Column(db.String(50), default='Pending')
#     order = db.relationship('Order', backref='shipping_details')  # Relationship to Order

#     def __repr__(self):
#         return f'<Shipping {self.shipping_id}>'


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



@app.route('/manufacturing-management/', methods=["GET", "POST"])
def manufacturing_management():
    orders = Order.query.all()  # Get all orders
    if request.method == "POST":
        order_id = request.form.get('order_id')
        batch_id = request.form.get('batch_id')
        produced_quantity = request.form.get('produced_quantity', type=int)

        if not produced_quantity or produced_quantity <= 0:
            flash("Please enter a valid quantity.", "danger")
            return redirect(url_for('manufacturing_management'))

        order = Order.query.get_or_404(order_id)
        batch = ProductionBatch.query.get_or_404(batch_id)

        # Update batch status and produced quantity
        batch.produced_quantity += produced_quantity
        db.session.commit()

        # Check if the order is complete
        total_produced = sum([b.produced_quantity for b in order.production_batches])
        if total_produced >= order.total_quantity:
            order.status = "Completed"
            for b in order.production_batches:
                b.batch_status = "Completed"
            db.session.commit()

        flash("Batch updated successfully.", "success")
        return redirect(url_for('manufacturing_management'))

    return render_template('manufacturing_management.html', orders=orders)


# @app.route('/process-batch/<int:batch_id>', methods=["POST"])
# def process_batch(batch_id):
#     batch = Product.query.get_or_404(batch_id)

#     if batch.is_incomplete():  # Kiểm tra xem lô sản phẩm có hoàn chỉnh hay không
#         flash("Cannot proceed with incomplete batch.", "danger")
#         return redirect(url_for('manufacturing_management'))
    
#     # Xử lý lô sản phẩm
#     batch.pro_status = "Ready for Shipment"
#     db.session.commit()
#     flash("Batch processed successfully.", "success")
#     return redirect(url_for('manufacturing_management'))
# @app.route('/update-status/<int:product_id>', methods=["POST"])
# def update_status(product_id):
#     product = Product.query.get_or_404(product_id)
#     new_status = request.form.get('status')

#     valid_statuses = ['In Production', 'Completed', 'Ready for Shipment']
#     if new_status in valid_statuses:
#         if product.pro_status == 'Ready for Shipment' and new_status == 'In Production':
#             flash("Status change not allowed.", "danger")
#             return redirect(url_for('viewProduct'))
#         product.pro_status = new_status
#         db.session.commit()
#         flash("Product status updated successfully.", "success")
#     else:
#         flash("Invalid status transition.", "danger")
    
#     return redirect(url_for('manufacturing_management'))
# @app.route('/record-condition/<int:product_id>', methods=["POST"])
# def record_condition(product_id):
#     product = Product.query.get_or_404(product_id)
#     condition = request.form.get('condition')
#     defect_reason = request.form.get('defect_reason')

#     if condition == "Defective" and not defect_reason:
#         flash("Defect reason required.", "danger")
#         return redirect(url_for('manufacturing_management'))

#     product.condition = condition
#     if condition == "Defective":
#         product.defect_reason = defect_reason
    
#     db.session.commit()
#     flash("Product condition updated successfully.", "success")
#     return redirect(url_for('manufacturing_management'))
# @app.route('/update-quantity/<int:product_id>', methods=["POST"])
# def update_quantity(product_id):
#     product = Product.query.get_or_404(product_id)
#     quantity_to_update = int(request.form.get('quantity'))

#     if quantity_to_update < 0:
#         flash("It must positive.", "danger")
#         return redirect(url_for('manufacturing_management'))

#     if quantity_to_update > product.pro_stock:
#         flash("Invalid quantity. Cannot exceed available stock.", "danger")
#         return redirect(url_for('manufacturing_management'))

#     product.pro_stock = quantity_to_update
#     db.session.commit()
#     flash("Product quantity updated successfully.", "success")
#     return redirect(url_for('manufacturing_management'))

# @app.route('/shipping/', methods=["GET", "POST"])
# def shipping():
#     # Lấy tất cả các đơn vận chuyển
#     shippings = Shipping.query.all()

#     if request.method == "POST":
#         order_id = request.form['order_id']  # Lấy ID đơn hàng từ form
#         provider = request.form['provider']  # Lấy nhà cung cấp từ form
#         tracking_code = request.form['tracking_code']  # Mã vận chuyển
#         status = request.form['status']  # Trạng thái vận chuyển

#         # Tạo bản ghi mới cho Shipping
#         new_shipping = Shipping(
#             order_id=order_id,
#             provider=provider,
#             tracking_code=tracking_code,
#             status=status
#         )

#         try:
#             db.session.add(new_shipping)
#             db.session.commit()
#             flash("Shipping order created successfully.", "success")
#             return redirect(url_for('view_shipping', shipping_id=new_shipping.shipping_id))  # Chuyển hướng đến trang vận chuyển mới
#         except Exception as e:
#             db.session.rollback()
#             flash("Shipping order processing failed. Please try again.", "danger")
#             return redirect(url_for('shipping'))  # Quay lại trang nếu có lỗi

#     return render_template('shipping.html', shippings=shippings)
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









@app.route("/dub-products/", methods=["POST"])
def getProductDuplicate():
    if request.method == "POST":
        product_name = request.form["product_name"]
        products = Product.query.filter(Product.pro_name == product_name).all()

        if products:
            return jsonify({"output": False})  # Name exists
        else:
            return jsonify({"output": True})  # Name is unique


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
    