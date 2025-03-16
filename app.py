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

# # Bảng Khách hàng
class Customer(db.Model):

    __tablename__     = 'customer'
    cus_id            = db.Column(db.Integer, primary_key=True)
    cus_name          = db.Column(db.String(255), nullable=False)
    cus_contact       = db.Column(db.String(255), nullable=False)
    cus_address       = db.Column(db.String(255), nullable=False)


    def __repr__(self):
        return '<Customer %r>' % self.cus_id
class Material(db.Model):
    __tablename__ = 'material'
    material_id = db.Column(db.Integer, primary_key=True)
    material_name = db.Column(db.String(255), nullable=False)
    material_description = db.Column(db.String(255))
    quantity_in_stock = db.Column(db.Integer, default=0)
    reorder_level = db.Column(db.Integer, default=10)
  

# # Bảng Nhà cung cấp
class Supplier(db.Model):

    __tablename__    = 'supplier'
    supplier_id      = db.Column(db.Integer, primary_key=True)
    sup_name         = db.Column(db.String(255), nullable=False)
    sup_contact_info = db.Column(db.String(255), nullable=False)
    sup_address      = db.Column(db.String(255), nullable=False)
    sup_material_id = db.Column(db.Integer, db.ForeignKey('material.material_id'))  # Sửa lại tên khóa ngoại
    material = db.relationship('Material', backref='supplier')

    def __repr__(self):
        return '<Supplier %r>' % self.supplier_id

# Bảng Sản phẩm
class Product(db.Model):
    __tablename__ = 'products'
    product_id = db.Column(db.Integer, primary_key=True)
    pro_name = db.Column(db.String(255), nullable=False)
    pro_category = db.Column(db.String(255))
    pro_unit_price = db.Column(db.Numeric(10, 2), nullable=False)
    pro_stock = db.Column(db.Integer, default=0)
    pro_reorder_level = db.Column(db.Integer, default=5)
    pro_supplier_id = db.Column(db.Integer, db.ForeignKey('supplier.supplier_id'))  # Sửa lại tên khóa ngoại
    supplier = db.relationship('Supplier', backref='products')
    last_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    condition = db.Column(db.String(50), nullable=True)
    defect_reason = db.Column(db.String(255), nullable=True)
    pro_status = db.Column(db.String(50), default='In Production')
    
    def __repr__(self):
        return f'<Product {self.product_id}>'
    
    def is_incomplete(self):
        return self.pro_stock < self.pro_reorder_level

# # Bảng Đơn hàng
class Order(db.Model):

    __tablename__ = 'order'
    order_id      = db.Column(db.Integer, primary_key=True)
    cus_id   = db.Column(db.Integer, db.ForeignKey('customer.cus_id'))
    order_date    = db.Column(db.DateTime, default=datetime.utcnow)
    price         = db.Column(db.Numeric(10, 2), nullable=False)
    status        = db.Column(db.String(50), default='Pending')
    customer      = db.relationship('Customer', backref='orders')

    def __repr__(self):
        return '<Order %r>' % self.order_id

# # Bảng Chi tiết Đơn hàng
class OrderDetail(db.Model):
    __tablename__ = 'oderdetail'
    oderde_id     = db.Column(db.Integer, primary_key=True)
    order_id      = db.Column(db.Integer, db.ForeignKey('order.order_id'))  # Ensure this points to the `order` table correctly
    product_id    = db.Column(db.Integer, db.ForeignKey('products.product_id'))  # Ensure this points to `product_id` in `Product`
    quantity      = db.Column(db.Integer, nullable=False)
    unit_price    = db.Column(db.Numeric(10, 2), nullable=False)

    order = db.relationship('Order', backref='order_details')
    product = db.relationship('Product', backref='order_details')

    def __repr__(self):
        return f'<OrderDetail {self.oderde_id}>'
class DepositConFirm(db.Model):
    __tablename__ = 'deposit_confirm'
    id = db.Column(db.Integer, primary_key=True)  # Khoá chính của bảng
    order_id = db.Column(db.Integer, db.ForeignKey('order.order_id'), nullable=False)  # Mã đơn hàng (khóa ngoại)
    deposit_amount = db.Column(db.Numeric(10, 2), nullable=False)  # Số tiền gửi
    transaction_date = db.Column(db.DateTime, default=datetime.utcnow)  # Ngày giao dịch

    order = db.relationship('Order', backref='deposit_confirm')  # Quan hệ với bảng Order

    def __repr__(self):
        return f'<DepositConfirm {self.id}>'
    
class PurchaseRequest(db.Model):
    __tablename__ = 'purchase_request'
    id = db.Column(db.Integer, primary_key=True)
    material_id = db.Column(db.Integer, db.ForeignKey('material.material_id'))
    quantity_requested = db.Column(db.Integer, nullable=False)
    transaction_date = db.Column(db.DateTime, default=datetime.utcnow)

    material = db.relationship('Material', backref='purchase_requests')

    def __repr__(self):
        return f'<PurchaseRequest {self.id}>'


class StockTransaction(db.Model):
    __tablename__ = 'stockTransaction'
    stockTran_id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.product_id'))
    material_id=db.Column(db.Integer,db.ForeignKey('material.material_id'))
    transaction_type = db.Column(db.String(50), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    transaction_date = db.Column(db.DateTime, default=datetime.utcnow)

    product = db.relationship('Product', backref='transactions') 
    material = db.relationship('Material', backref='transactions') # Đảm bảo quan hệ này


    def __repr__(self):
        return f'<StockTransaction {self.stockTran_id}>'




# # Bảng Thanh toán
class Payment(db.Model):

    __tablename__ = 'payment'
    payment_id    = db.Column(db.Integer, primary_key=True)
    order_id      = db.Column(db.Integer, db.ForeignKey('order.order_id'))
    amount        = db.Column(db.Numeric(10, 2), nullable=False)
    status        = db.Column(db.String(50), default='Pending')
    payment_date  = db.Column(db.DateTime, default=datetime.utcnow)
    order         = db.relationship('Order', backref='payments')

    def __repr__(self):
        return '<Payment %r>' % self.payment_id

# # Bảng Vận chuyển
class Shipping(db.Model):

    __tablename__ = 'shipping'
    shipping_id   = db.Column(db.Integer, primary_key=True)
    order_id      = db.Column(db.Integer, db.ForeignKey('order.order_id'))
    provider      = db.Column(db.String(255))
    tracking_code = db.Column(db.String(255), unique=True)
    status        = db.Column(db.String(50), default='Pending')
    order         = db.relationship('Order', backref='shipping')

    def __repr__(self):
        return '<Shipping %r>' % self.shipping_id

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
@app.route('/', methods=["POST", "GET"])
def index():
    # Lấy tất cả các sản phẩm từ cơ sở dữ liệu
    products = Product.query.all()  # Đảm bảo có dữ liệu
    print("Products:", products)  # In dữ liệu ra console để kiểm tra
    return render_template('index.html', products=products)


@app.route('/customer/', methods=["POST", "GET"])
def viewCustomer():
    # Kiểm tra phương thức request
    if request.method == "POST" and 'cus_name' in request.form:
        cus_name = request.form["cus_name"]
        cus_contact=request.form.get("cus_contact", "")
        cus_address = request.form.get("cus_address", "")
       

        # Tạo nhà cung cấp mới
        new_cus = Customer(
            cus_name=cus_name,
            cus_contact=cus_contact,
            cus_address=cus_address,
                    
        )

        try:
            db.session.add(new_cus)
            db.session.commit()
            return redirect("/customer/")  # Điều hướng lại về trang danh sách nhà cung cấp
        except Exception as e:
            return f"There was an issue adding a new Customer: {str(e)}"

    # Nếu là GET request, hoặc không có form POST, hiển thị danh sách nhà cung cấp
    customers = Customer.query.all()
    return render_template("customer.html", customers=customers)  # Trả về template danh sách nhà cung cấp
@app.route("/update-customer/<int:cus_id>", methods=["POST", "GET"])
def updateCustomer(cus_id):
    customer = Customer.query.get_or_404(cus_id)
    

    if request.method == "POST":
        customer.cus_name = request.form['cus_name']
        customer.cus_contact = request.form.get('cus_contact', customer.cus_contact)
        customer.cus_address = request.form.get('cus_address', customer.cus_address)
      
        
        try:
            db.session.commit()
            return redirect("/customer/")
        except:
            return "There was an issue while updating the customer"

    return render_template("update-customer.html", customer=customer)

@app.route("/delete-customer/<int:cus_id>")
def deleteCustomer(cus_id):
    customer_to_delete = Customer.query.get_or_404(cus_id)

    try:
        db.session.delete(customer_to_delete)
        db.session.commit()
        return redirect("/customer/")
    except:
        return "There was an issue while deleting the customer"
@app.route('/material/', methods=["POST", "GET"])
def view_material():
    if request.method == "POST":
        material_name = request.form["material_name"]
        material_description = request.form.get("material_description", "")
        quantity_in_stock = int(request.form.get("quantity_in_stock", 0))
        reorder_level = int(request.form.get("reorder_level", 10))

        # Tạo vật liệu mới
        new_material = Material(
            material_name=material_name,
            material_description=material_description,
            quantity_in_stock=quantity_in_stock,
            reorder_level=reorder_level
        )

        try:
            db.session.add(new_material)
            db.session.commit()
            new_transaction = StockTransaction(
                material_id=new_material.material_id,
                transaction_type="Addition",  # Loại giao dịch là nhập kho
                quantity=quantity_in_stock,  # Số lượng đã thêm vào kho
                
            )
            db.session.add(new_transaction)
            db.session.commit()
            
            flash("Material added successfully!", "success")
            
            return redirect(url_for('view_material'))
        except Exception as e:
            db.session.rollback()
            flash(f"Error adding material: {str(e)}", "danger")
    suppliers=Supplier.query.all()
    materials = Material.query.all()
    return render_template("material.html", materials=materials,suppliers=suppliers)


@app.route('/update-material/<int:material_id>', methods=["POST", "GET"])
def update_material(material_id):
    material = Material.query.get_or_404(material_id)

    if request.method == "POST":
        material.material_name = request.form['material_name']
        material.material_description = request.form.get('material_description', '')
        material.quantity_in_stock = int(request.form.get('quantity_in_stock', 0))
        material.reorder_level = int(request.form.get('reorder_level', 10))

        try:
            db.session.commit()
            flash("Material updated successfully!", "success")
            return redirect(url_for('view_material'))
        except Exception as e:
            db.session.rollback()
            flash(f"Error updating material: {str(e)}", "danger")

    return render_template("update_material.html", material=material)
@app.route('/delete-material/<int:material_id>', methods=["POST"])
def delete_material(material_id):
    material = Material.query.get_or_404(material_id)

    try:
        db.session.delete(material)
        db.session.commit()
        flash("Material deleted successfully!", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error deleting material: {str(e)}", "danger")

    return redirect(url_for('view_material'))


@app.route('/supplier/', methods=["POST", "GET"])
def viewSupplier():
    materials=Material.query.all()
    # Kiểm tra phương thức request
    if request.method == "POST" and 'sup_name' in request.form:
        sup_name = request.form["sup_name"]     
        sup_material_id = request.form.get("sup_material_id", None)   
        sup_contact_info = request.form.get("sup_contact_info", "")
        sup_address = request.form.get("sup_address", "")
        

        # Tạo nhà cung cấp mới
        new_sup = Supplier(
            sup_name=sup_name,
            sup_material_id=sup_material_id,
            sup_contact_info=sup_contact_info,
            sup_address=sup_address,            
        )

        try:
            db.session.add(new_sup)
            db.session.commit()
            return redirect("/supplier/")  # Điều hướng lại về trang danh sách nhà cung cấp
        except Exception as e:
            return f"There was an issue adding a new supplier: {str(e)}"

    # Nếu là GET request, hoặc không có form POST, hiển thị danh sách nhà cung cấp
    suppliers = Supplier.query.all()
    return render_template("supplier.html", suppliers=suppliers,materials=materials)  # Trả về template danh sách nhà cung cấp
@app.route("/update-supplier/<int:supplier_id>", methods=["POST", "GET"])
def updateSupplier(supplier_id):
    supplier = Supplier.query.get_or_404(supplier_id)
    

    if request.method == "POST":
        supplier.sup_name = request.form['sup_name']
        supplier.sup_material_id = request.form.get('sup_material_id', supplier.sup_material_id)
        supplier.sup_contact_info = request.form.get('sup_contact_info', supplier.sup_contact_info)
        supplier.sup_address = request.form.get('sup_address', supplier.sup_address)
        
        try:
            db.session.commit()
            return redirect("/supplier/")
        except:
            return "There was an issue while updating the supplier"
    materials=Material.query.all()
    return render_template("update-supplier.html", supplier=supplier,materials=materials)

@app.route("/delete-supplier/<int:supplier_id>")
def deleteSupplier(supplier_id):
    supplier_to_delete = Supplier.query.get_or_404(supplier_id)

    try:
        db.session.delete(supplier_to_delete)
        db.session.commit()
        return redirect("/supplier/")
    except:
        return "There was an issue while deleting the supplier"


@app.route('/products/', methods=["POST", "GET"])
def viewProduct():
    # Lấy danh sách nhà cung cấp
    suppliers = Supplier.query.all()

    if request.method == "POST" and 'product_name' in request.form:
        product_name = request.form["product_name"]
        pro_category = request.form.get("pro_category", "")
        pro_unit_price = request.form.get("pro_unit_price", 0)
        pro_stock = request.form.get("pro_stock", 0)
        pro_reorder_level = request.form.get("pro_reorder_level", 5)
        pro_supplier_id = request.form.get("pro_supplier_id", None)

        # Tạo sản phẩm mới với thông tin nhập vào
        new_product = Product(
            pro_name=product_name,
            pro_category=pro_category,
            pro_unit_price=pro_unit_price,
            pro_stock=pro_stock,
            pro_reorder_level=pro_reorder_level,
            pro_supplier_id=pro_supplier_id
        )

        try:
            db.session.add(new_product)
            db.session.commit()  # Lưu sản phẩm mới vào cơ sở dữ liệu

            # Tạo Stock Transaction tự động sau khi thêm sản phẩm
            new_transaction = StockTransaction(
                product_id=new_product.product_id,
                transaction_type="Addition",  # Loại giao dịch là nhập kho
                quantity=pro_stock,  # Số lượng đã thêm vào kho
                transaction_date=datetime.utcnow()
            )
            db.session.add(new_transaction)
            db.session.commit()  # Lưu giao dịch kho vào cơ sở dữ liệu

            flash("Product and stock transaction added successfully!", "success")
            return redirect("/products/")  # Điều hướng lại về trang danh sách sản phẩm
        except Exception as e:
            db.session.rollback()  # Nếu có lỗi, rollback lại
            flash(f"There was an issue adding the product: {str(e)}", "danger")
            return redirect("/products/")  # Quay lại trang danh sách sản phẩm

    # Nếu là GET request, hoặc không có form POST, hiển thị sản phẩm và danh sách nhà cung cấp
    products = Product.query.order_by(Product.last_updated.desc()).all()
    return render_template("products.html", products=products, suppliers=suppliers)


@app.route("/update-product/<int:product_id>", methods=["POST", "GET"])
def updateProduct(product_id):
    product = Product.query.get_or_404(product_id)

    if request.method == "POST":
        product.pro_name = request.form['product_name']
        product.pro_category = request.form.get('pro_category', product.pro_category)
        product.pro_unit_price = request.form.get('pro_unit_price', product.pro_unit_price)
        product.pro_stock = request.form.get('pro_stock', product.pro_stock)
        product.pro_reorder_level = request.form.get('pro_reorder_level', product.pro_reorder_level)
        product.pro_supplier_id = request.form.get('pro_supplier_id', product.pro_supplier_id)

        try:
            db.session.commit()
            return redirect("/products/")
        except:
            return "There was an issue while updating the Product"

    suppliers = Supplier.query.all()  # Lấy danh sách nhà cung cấp
    return render_template("update-product.html", product=product, suppliers=suppliers)


@app.route("/delete-product/<int:product_id>")
def deleteProduct(product_id):
    product_to_delete = Product.query.get_or_404(product_id)

    try:
        db.session.delete(product_to_delete)
        db.session.commit()
        return redirect("/products/")
    except:
        return "There was an issue while deleting the Product"
    
from datetime import datetime

@app.route('/order/', methods=["POST", "GET"])
def viewOrder():
    if request.method == "POST":
        # Handle form submission to add a new order
        cus_id = request.form['cus_id']
        price = request.form['price']
        status = request.form['status']

        # Create a new order
        new_order = Order(
            cus_id=cus_id,
            price=price,
            status=status
        )

        # Add the order to the session and commit
        db.session.add(new_order)
        db.session.commit()

        # Now create order details for each product in the order
        product_ids = request.form.getlist('product_ids')  # Assuming the products are passed as a list of product IDs
        quantities = request.form.getlist('quantities')  # The quantities for each product

        for product_id, quantity in zip(product_ids, quantities):
            product = Product.query.get(product_id)
            order_detail = OrderDetail(
                order_id=new_order.order_id,
                product_id=product_id,
                quantity=quantity,
                unit_price=product.pro_unit_price
            )
            db.session.add(order_detail)

        db.session.commit()

        return redirect("/order/")  # Redirect to the order page to see the updated list

    # GET request: Show orders and customers
    orders = Order.query.all()  # Fetch all orders from the database
    customers = Customer.query.all()  # Fetch all customers to populate the customer dropdown
    products = Product.query.all()  # Fetch all products to populate the product dropdown

    return render_template("order.html", orders=orders, customers=customers, products=products)


@app.route("/update-order/<int:order_id>", methods=["POST", "GET"])
def updateOrder(order_id):
    order = Order.query.get_or_404(order_id)
    customers = Customer.query.all()
    products = Product.query.all()

    if request.method == "POST":
        order.customer_id = request.form['customer_id']
        order.status = request.form['status']
        
        # Cập nhật ngày đơn hàng
        order_date_str = request.form['order_date']
        order.order_date = datetime.strptime(order_date_str, '%Y-%m-%dT%H:%M')

        # Lấy danh sách chi tiết đơn hàng (sản phẩm và số lượng)
        product_ids = request.form.getlist('product_ids')  # Danh sách product_ids
        quantities = request.form.getlist('quantities')  # Danh sách số lượng cho mỗi sản phẩm

        # Kiểm tra tồn kho cho mỗi sản phẩm trong đơn hàng
        for product_id, quantity in zip(product_ids, quantities):
            product = Product.query.get(product_id)
            if product.pro_stock < int(quantity):  # Nếu không đủ tồn kho
                flash(f"Not enough stock for product: {product.pro_name}. Available stock: {product.pro_stock}", "danger")
                db.session.rollback()  # Rollback giao dịch
                return redirect(url_for('viewOrder'))

            # Cập nhật số lượng tồn kho sau khi đơn hàng được xác nhận
            product.pro_stock -= int(quantity)
            # Cập nhật chi tiết đơn hàng
            order_detail = OrderDetail.query.filter_by(order_id=order.order_id, product_id=product_id).first()
            order_detail.quantity = int(quantity)
            order_detail.unit_price = product.pro_unit_price

        try:
            db.session.commit()  # Lưu cập nhật vào cơ sở dữ liệu
            flash("Order updated successfully!", "success")
            return redirect("/order/")  # Quay lại trang danh sách đơn hàng
        except Exception as e:
            db.session.rollback()  # Rollback nếu có lỗi
            flash(f"There was an issue while updating the order: {str(e)}", "danger")

    return render_template("update-order.html", order=order, customers=customers, products=products)

@app.route("/delete-order/<int:order_id>", methods=["POST"])
def deleteOrder(order_id):
    # Get the order that we want to delete
    order_to_delete = Order.query.get_or_404(order_id)

    try:
        db.session.delete(order_to_delete)  # Delete the order
        db.session.commit()  # Commit the change to the database
        return redirect("/order/")  # Redirect to the orders list after deletion
    except Exception as e:
        return f"There was an issue while deleting the order: {str(e)}"  # Handle error
@app.route("/order-detail/<int:order_id>")
def orderDetail(order_id):
    order = Order.query.get_or_404(order_id)  # Get the order by ID
    return render_template("order-detail.html", order=order)
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
            flash("Deposit insufficient. Please try again.", "danger")
            return redirect(url_for('deposit_confirm'))

        # Thêm giao dịch gửi tiền vào cơ sở dữ liệu
        deposit_confirm = DepositConFirm(
            order_id=order.order_id,
            deposit_amount=deposit_amount,
            transaction_date=datetime.utcnow()
        )
        db.session.add(deposit_confirm)
        db.session.commit()

        flash("Deposit recorded successfully.", "success")
        # return redirect(url_for('order-detail', order_id=order.order_id))  # Chuyển hướng đến chi tiết đơn hàng
    return render_template("deposit_confirm.html")

@app.route('/inventory/', methods=["GET"])
def inventory():
    # Lấy tất cả các sản phẩm, giao dịch kho và vật liệu
    products = Product.query.all()  # Lấy tất cả sản phẩm
    transactions = StockTransaction.query.all()  # Lấy tất cả giao dịch kho
    materials = Material.query.all()  # Lấy tất cả vật liệu
    return render_template('inventory.html', products=products, transactions=transactions, materials=materials)


@app.route("/delete-transaction/<int:transaction_id>", methods=["GET", "POST"])
def delete_transaction(transaction_id):
    transaction = StockTransaction.query.get_or_404(transaction_id)
    
    try:
        db.session.delete(transaction)  # Xóa giao dịch kho
        db.session.commit()  # Commit thay đổi vào cơ sở dữ liệu
        flash("Transaction deleted successfully!", "success")
    except Exception as e:
        db.session.rollback()  # Rollback nếu có lỗi
        flash(f"Error deleting transaction: {str(e)}", "danger")
    
    return redirect(url_for('inventory'))  # Quay lại trang Inventory


@app.route('/create-purchase-request/<int:material_id>', methods=["GET", "POST"])
def create_purchase_request(material_id):
    material = Material.query.get_or_404(material_id)

    if material.quantity_in_stock < material.reorder_level:
        if request.method == "POST":
            quantity_to_order = request.form.get("quantity", type=int)

            if quantity_to_order and quantity_to_order > 0:
                # Lưu yêu cầu mua hàng vào cơ sở dữ liệu
                new_purchase_request = StockTransaction(
                    material_id=material_id,
                    transaction_type="Purchase Request",  # Loại giao dịch là yêu cầu mua hàng
                    quantity=quantity_to_order,
                    transaction_date=datetime.utcnow()
                )
                db.session.add(new_purchase_request)
                db.session.commit()

                # Cập nhật kho ngay lập tức
                material.quantity_in_stock += quantity_to_order
                db.session.commit()

                flash("Purchase request created and stock updated successfully.", "success")
                return redirect(url_for('inventory'))  # Quay lại trang kiểm tra tồn kho

            else:
                flash("Invalid quantity!", "danger")

        return render_template("create_purchase_request.html", material=material)

    flash("Stock level is sufficient. No purchase request needed.", "info")
    return redirect(url_for('inventory'))



@app.route('/manufacturing-management/', methods=["GET", "POST"])
def manufacturing_management():
    # Lấy tất cả sản phẩm
    products = Product.query.all()
    good_products = Product.query.filter_by(condition="Good").all()
    defective_products = Product.query.filter_by(condition="Defective").all()

    if request.method == "POST":
        product_id = request.form.get('product_id')
        status = request.form.get('status')
        condition = request.form.get('condition')
        defect_reason = request.form.get('defect_reason', None)

        if not product_id:
            flash("Please select a product.", "danger")
            return redirect(url_for('manufacturing_management'))

        product = Product.query.get_or_404(product_id)

        # Kiểm tra nếu sản phẩm bị lỗi nhưng không có lý do
        if condition == "Defective" and not defect_reason:
            flash("Defect reason required.", "danger")
            return redirect(url_for('manufacturing_management'))

        product.pro_status = status
        product.condition = condition
        if condition == "Defective":
            product.defect_reason = defect_reason
        db.session.commit()

        flash("Product status and condition updated successfully.", "success")
        return redirect(url_for('manufacturing_management'))

    return render_template('manufacturing_management.html', products=products, good_products=good_products, defective_products=defective_products)



# Route xử lý lô sản phẩm chưa hoàn chỉnh
@app.route('/process-batch/<int:batch_id>', methods=["POST"])
def process_batch(batch_id):
    batch = Product.query.get_or_404(batch_id)

    if batch.is_incomplete():  # Kiểm tra xem lô sản phẩm có hoàn chỉnh hay không
        flash("Cannot proceed with incomplete batch.", "danger")
        return redirect(url_for('manufacturing_management'))
    
    # Xử lý lô sản phẩm
    batch.pro_status = "Ready for Shipment"
    db.session.commit()
    flash("Batch processed successfully.", "success")
    return redirect(url_for('manufacturing_management'))


# Route xử lý thay đổi trạng thái sản phẩm
@app.route('/update-status/<int:product_id>', methods=["POST"])
def update_status(product_id):
    product = Product.query.get_or_404(product_id)
    new_status = request.form.get('status')

    valid_statuses = ['In Production', 'Completed', 'Ready for Shipment']
    if new_status in valid_statuses:
        if product.pro_status == 'Ready for Shipment' and new_status == 'In Production':
            flash("Status change not allowed.", "danger")
            return redirect(url_for('viewProduct'))
        product.pro_status = new_status
        db.session.commit()
        flash("Product status updated successfully.", "success")
    else:
        flash("Invalid status transition.", "danger")
    
    return redirect(url_for('manufacturing_management'))


# Kiểm tra tình trạng sản phẩm
@app.route('/record-condition/<int:product_id>', methods=["POST"])
def record_condition(product_id):
    product = Product.query.get_or_404(product_id)
    condition = request.form.get('condition')
    defect_reason = request.form.get('defect_reason')

    if condition == "Defective" and not defect_reason:
        flash("Defect reason required.", "danger")
        return redirect(url_for('manufacturing_management'))

    product.condition = condition
    if condition == "Defective":
        product.defect_reason = defect_reason
    
    db.session.commit()
    flash("Product condition updated successfully.", "success")
    return redirect(url_for('manufacturing_management'))

# Route cho việc cập nhật số lượng sản phẩm
@app.route('/update-quantity/<int:product_id>', methods=["POST"])
def update_quantity(product_id):
    product = Product.query.get_or_404(product_id)
    quantity_to_update = int(request.form.get('quantity'))

    if quantity_to_update < 0:
        flash("It must positive.", "danger")
        return redirect(url_for('manufacturing_management'))

    if quantity_to_update > product.pro_stock:
        flash("Invalid quantity. Cannot exceed available stock.", "danger")
        return redirect(url_for('manufacturing_management'))

    product.pro_stock = quantity_to_update
    db.session.commit()
    flash("Product quantity updated successfully.", "success")
    return redirect(url_for('manufacturing_management'))

@app.route('/shipping/', methods=["GET", "POST"])
def shipping():
    # Lấy tất cả các đơn vận chuyển
    shippings = Shipping.query.all()

    if request.method == "POST":
        order_id = request.form['order_id']  # Lấy ID đơn hàng từ form
        provider = request.form['provider']  # Lấy nhà cung cấp từ form
        tracking_code = request.form['tracking_code']  # Mã vận chuyển
        status = request.form['status']  # Trạng thái vận chuyển

        # Tạo bản ghi mới cho Shipping
        new_shipping = Shipping(
            order_id=order_id,
            provider=provider,
            tracking_code=tracking_code,
            status=status
        )

        try:
            db.session.add(new_shipping)
            db.session.commit()
            flash("Shipping order created successfully.", "success")
            return redirect(url_for('view_shipping', shipping_id=new_shipping.shipping_id))  # Chuyển hướng đến trang vận chuyển mới
        except Exception as e:
            db.session.rollback()
            flash("Shipping order processing failed. Please try again.", "danger")
            return redirect(url_for('shipping'))  # Quay lại trang nếu có lỗi

    return render_template('shipping.html', shippings=shippings)
@app.route('/shippings/<int:shipping_id>', methods=["GET"])
def view_shipping(shipping_id):
    shipping = Shipping.query.get_or_404(shipping_id)
    return render_template('view_shipping.html', shipping=shipping)

@app.route('/cancel-shipping/<int:shipping_id>', methods=["POST"])
def cancel_shipping(shipping_id):
    shipping = Shipping.query.get_or_404(shipping_id)  # Lấy thông tin đơn vận chuyển
    try:
        db.session.delete(shipping)  # Xóa đơn vận chuyển
        db.session.commit()
        flash("Shipping process has been successfully canceled.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Failed to cancel shipping. Please try again. Error: {str(e)}", "danger")

    return redirect(url_for('shipping'))  # Quay lại trang quản lý vận chuyển










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
    