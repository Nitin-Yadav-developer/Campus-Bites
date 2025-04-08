from flask import render_template, request, redirect, url_for, flash, jsonify, session
from flask_login import login_user, logout_user, login_required, current_user
from app import app, db
from app import User, Product, Category, Order, OrderItem, Cart, Favorite, Vendor
from werkzeug.security import generate_password_hash, check_password_hash
import uuid
import datetime
from math import ceil
from sqlalchemy.exc import IntegrityError
from functools import wraps

# Admin authentication decorator
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('You do not have permission to access this page', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

# Vendor authentication decorator
def vendor_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_vendor():
            flash('You do not have permission to access this page', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

# Home page route
@app.route('/')
def index():
    # Get food and snacks categories
    food_category = Category.query.filter_by(name='Food').first()
    snacks_category = Category.query.filter_by(name='Snacks').first()
    
    # Get products for each category
    food_items = []
    snack_items = []
    
    if food_category:
        food_items = Product.query.filter_by(category_id=food_category.id, is_available=True).all()
    
    if snacks_category:
        snack_items = Product.query.filter_by(category_id=snacks_category.id, is_available=True).all()
    
    return render_template('index.html', food_items=food_items, snack_items=snack_items)

# Edit profile route
@app.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        name = request.form.get('name')
        mobile_number = request.form.get('mobile_number')
        university = request.form.get('university')
        
        # Check if username is changed and if it's already taken
        if username != current_user.username:
            existing_user = User.query.filter_by(username=username).first()
            if existing_user:
                flash('Username already exists!', 'danger')
                return redirect(url_for('edit_profile'))
        
        # Check if email is changed and if it's already taken
        if email != current_user.email:
            existing_email = User.query.filter_by(email=email).first()
            if existing_email:
                flash('Email already registered!', 'danger')
                return redirect(url_for('edit_profile'))
        
        # Update user information
        current_user.username = username
        current_user.email = email
        current_user.name = name
        current_user.mobile_number = mobile_number
        current_user.university = university
        
        db.session.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('profile'))
    
    return render_template('edit_profile.html')

# Change password route
@app.route('/profile/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    if request.method == 'POST':
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        # Check if current password is correct
        if not current_user.check_password(current_password):
            flash('Current password is incorrect!', 'danger')
            return redirect(url_for('change_password'))
        
        # Check if new passwords match
        if new_password != confirm_password:
            flash('New passwords do not match!', 'danger')
            return redirect(url_for('change_password'))
        
        # Update password
        current_user.set_password(new_password)
        db.session.commit()
        
        flash('Password changed successfully!', 'success')
        return redirect(url_for('profile'))
    
    return render_template('change_password.html')

# View all snacks with pagination
@app.route('/snacks')
def view_all_snacks():
    page = request.args.get('page', 1, type=int)
    per_page = 8  # 8 items per page (2 rows of 4)
    
    snacks_category = Category.query.filter_by(name='Snacks').first()
    
    if not snacks_category:
        flash('Snacks category not found', 'danger')
        return redirect(url_for('index'))
    
    # Get paginated snacks
    pagination = Product.query.filter_by(
        category_id=snacks_category.id, 
        is_available=True
    ).paginate(page=page, per_page=per_page, error_out=False)
    
    snack_items = pagination.items
    total_pages = pagination.pages
    
    return render_template(
        'category_items.html',
        items=snack_items,
        pagination=pagination,
        category_name='Snacks',
        category_icon='fas fa-cookie-bite',
        current_page=page,
        total_pages=total_pages
    )

# View all food items with pagination
@app.route('/food')
def view_all_food():
    page = request.args.get('page', 1, type=int)
    per_page = 8  # 8 items per page (2 rows of 4)
    
    food_category = Category.query.filter_by(name='Food').first()
    
    if not food_category:
        flash('Food category not found', 'danger')
        return redirect(url_for('index'))
    
    # Get paginated food items
    pagination = Product.query.filter_by(
        category_id=food_category.id, 
        is_available=True
    ).paginate(page=page, per_page=per_page, error_out=False)
    
    food_items = pagination.items
    total_pages = pagination.pages
    
    return render_template(
        'category_items.html',
        items=food_items,
        pagination=pagination,
        category_name='Campus Food',
        category_icon='fas fa-utensils',
        current_page=page,
        total_pages=total_pages
    )

# Login route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
        
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user)
            next_page = request.args.get('next')
            flash('Login successful!', 'success')
            return redirect(next_page or url_for('index'))
        else:
            flash('Invalid username or password', 'danger')
    
    return render_template('login.html')

# Register route
@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
        
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        # Get new fields
        name = request.form.get('name')
        mobile_number = request.form.get('mobile_number')
        university = request.form.get('university')
        
        if password != confirm_password:
            flash('Passwords do not match!', 'danger')
            return redirect(url_for('register'))
        
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('Username already exists!', 'danger')
            return redirect(url_for('register'))
            
        existing_email = User.query.filter_by(email=email).first()
        if existing_email:
            flash('Email already registered!', 'danger')
            return redirect(url_for('register'))
        
        new_user = User(
            username=username, 
            email=email,
            name=name,
            mobile_number=mobile_number,
            university=university
        )
        new_user.set_password(password)
        
        db.session.add(new_user)
        db.session.commit()
        
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')

# Logout route
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out!', 'info')
    return redirect(url_for('index'))

# Add to cart route
@app.route('/add_to_cart/<int:product_id>', methods=['POST'])
@login_required
def add_to_cart(product_id):
    product = Product.query.get_or_404(product_id)
    quantity = int(request.form.get('quantity', 1))
    
    # Check if product is already in cart
    cart_item = Cart.query.filter_by(user_id=current_user.id, product_id=product_id).first()
    
    if cart_item:
        # Update quantity if product already in cart
        cart_item.quantity += quantity
    else:
        # Add new item to cart
        cart_item = Cart(user_id=current_user.id, product_id=product_id, quantity=quantity)
        db.session.add(cart_item)
    
    db.session.commit()
    flash(f'{product.name} added to cart!', 'success')
    
    return redirect(request.referrer or url_for('index'))

# View cart route
@app.route('/cart')
@login_required
def view_cart():
    cart_items = Cart.query.filter_by(user_id=current_user.id).all()
    total = sum(item.product.price * item.quantity for item in cart_items)
    
    return render_template('cart.html', cart_items=cart_items, total=total)

# Update cart item quantity
@app.route('/update_cart/<int:cart_id>', methods=['POST'])
@login_required
def update_cart(cart_id):
    cart_item = Cart.query.get_or_404(cart_id)
    
    if cart_item.user_id != current_user.id:
        flash('Unauthorized action!', 'danger')
        return redirect(url_for('view_cart'))
    
    quantity = int(request.form.get('quantity', 1))
    
    if quantity <= 0:
        db.session.delete(cart_item)
    else:
        cart_item.quantity = quantity
    
    db.session.commit()
    return redirect(url_for('view_cart'))

# Remove item from cart
@app.route('/remove_from_cart/<int:cart_id>')
@login_required
def remove_from_cart(cart_id):
    cart_item = Cart.query.get_or_404(cart_id)
    
    if cart_item.user_id != current_user.id:
        flash('Unauthorized action!', 'danger')
        return redirect(url_for('view_cart'))
    
    db.session.delete(cart_item)
    db.session.commit()
    
    flash('Item removed from cart!', 'success')
    return redirect(url_for('view_cart'))

# Checkout route
@app.route('/checkout')
@login_required
def checkout():
    cart_items = Cart.query.filter_by(user_id=current_user.id).all()
    
    if not cart_items:
        flash('Your cart is empty!', 'warning')
        return redirect(url_for('view_cart'))
    
    total = sum(item.product.price * item.quantity for item in cart_items)
    
    return render_template('checkout.html', cart_items=cart_items, total=total)

# Process order
@app.route('/place_order', methods=['POST'])
@login_required
def place_order():
    cart_items = Cart.query.filter_by(user_id=current_user.id).all()
    
    if not cart_items:
        flash('Your cart is empty!', 'warning')
        return redirect(url_for('view_cart'))
    
    total_amount = sum(item.product.price * item.quantity for item in cart_items)
    
    # Generate unique order number
    order_number = str(uuid.uuid4().hex)[:10].upper()
    
    # Create new order
    new_order = Order(
        user_id=current_user.id,
        total_amount=total_amount,
        order_number=order_number,
        status='pending'
    )
    
    db.session.add(new_order)
    db.session.flush()  # Flush to get the order ID
    
    # Create order items
    for cart_item in cart_items:
        order_item = OrderItem(
            order_id=new_order.id,
            product_id=cart_item.product_id,
            quantity=cart_item.quantity,
            price=cart_item.product.price
        )
        db.session.add(order_item)
    
    # Clear cart
    for cart_item in cart_items:
        db.session.delete(cart_item)
    
    db.session.commit()
    
    flash('Order placed successfully!', 'success')
    return redirect(url_for('order_success', order_id=new_order.id))

# Order success page
@app.route('/order_success/<int:order_id>')
@login_required
def order_success(order_id):
    order = Order.query.get_or_404(order_id)
    
    if order.user_id != current_user.id:
        flash('Unauthorized access!', 'danger')
        return redirect(url_for('index'))
    
    return render_template('order_success.html', order=order)

# User profile page
@app.route('/profile')
@login_required
def profile():
    user_orders = Order.query.filter_by(user_id=current_user.id).order_by(Order.order_date.desc()).all()
    return render_template('profile.html', user=current_user, orders=user_orders)

# View order details
@app.route('/order/<int:order_id>')
@login_required
def view_order(order_id):
    order = Order.query.get_or_404(order_id)
    
    if order.user_id != current_user.id:
        flash('Unauthorized access!', 'danger')
        return redirect(url_for('profile'))
    
    return render_template('order_details.html', order=order)

# Search products
@app.route('/search')
def search():
    query = request.args.get('query', '')
    products = Product.query.filter(Product.name.contains(query)).all()
    return render_template('search_results.html', products=products, query=query)

# Favorites routes
@app.route('/favorites')
@login_required
def view_favorites():
    favorites = Favorite.query.filter_by(user_id=current_user.id).order_by(Favorite.date_added.desc()).all()
    return render_template('favorites.html', favorites=favorites)

@app.route('/add_to_favorites/<int:product_id>')
@login_required
def add_to_favorites(product_id):
    product = Product.query.get_or_404(product_id)
    
    # Check if already in favorites
    existing_favorite = Favorite.query.filter_by(user_id=current_user.id, product_id=product_id).first()
    
    if existing_favorite:
        flash('Item already in favorites!', 'info')
    else:
        new_favorite = Favorite(user_id=current_user.id, product_id=product_id)
        db.session.add(new_favorite)
        try:
            db.session.commit()
            flash(f'{product.name} added to favorites!', 'success')
        except IntegrityError:
            db.session.rollback()
            flash('This item is already in your favorites!', 'warning')
    
    return redirect(request.referrer or url_for('index'))

@app.route('/remove_from_favorites/<int:product_id>')
@login_required
def remove_from_favorites(product_id):
    favorite = Favorite.query.filter_by(user_id=current_user.id, product_id=product_id).first_or_404()
    
    product_name = favorite.product.name
    db.session.delete(favorite)
    db.session.commit()
    
    flash(f'{product_name} removed from favorites!', 'success')
    return redirect(request.referrer or url_for('view_favorites'))

# Admin routes
@app.route('/admin')
@login_required
@admin_required
def admin_dashboard():
    # Get counts for dashboard
    user_count = User.query.count()
    order_count = Order.query.count()
    product_count = Product.query.count()
    vendor_count = Vendor.query.count()
    
    # Get recent orders
    recent_orders = Order.query.order_by(Order.order_date.desc()).limit(5).all()
    
    # Calculate total revenue
    total_revenue = db.session.query(db.func.sum(Order.total_amount)).scalar() or 0
    
    # Get order status counts for chart
    pending_count = Order.query.filter_by(status='pending').count()
    processing_count = Order.query.filter_by(status='processing').count()
    completed_count = Order.query.filter_by(status='completed').count()
    cancelled_count = Order.query.filter_by(status='cancelled').count()
    
    # Get monthly revenue data for chart
    current_year = datetime.datetime.now().year
    monthly_revenue = []
    
    for month in range(1, 13):
        start_date = datetime.datetime(current_year, month, 1)
        if month == 12:
            end_date = datetime.datetime(current_year + 1, 1, 1) - datetime.timedelta(days=1)
        else:
            end_date = datetime.datetime(current_year, month + 1, 1) - datetime.timedelta(days=1)
        
        month_revenue = db.session.query(db.func.sum(Order.total_amount)).filter(
            Order.order_date >= start_date,
            Order.order_date <= end_date
        ).scalar() or 0
        
        monthly_revenue.append(float(month_revenue))
    
    return render_template('admin/dashboard.html', 
                          user_count=user_count,
                          order_count=order_count,
                          product_count=product_count,
                          vendor_count=vendor_count,
                          recent_orders=recent_orders,
                          total_revenue=total_revenue,
                          order_status_counts=[pending_count, processing_count, completed_count, cancelled_count],
                          monthly_revenue=monthly_revenue,
                          now=datetime.datetime.now())

# Admin Users Management
@app.route('/admin/users')
@login_required
@admin_required
def admin_users():
    page = request.args.get('page', 1, type=int)
    per_page = 10
    
    users = User.query.paginate(page=page, per_page=per_page, error_out=False)
    
    return render_template('admin/users.html', users=users)

# Admin User Details/Edit
@app.route('/admin/users/<int:user_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_user_detail(user_id):
    user = User.query.get_or_404(user_id)
    
    if request.method == 'POST':
        user.username = request.form.get('username')
        user.email = request.form.get('email')
        user.name = request.form.get('name')
        user.mobile_number = request.form.get('mobile_number')
        user.university = request.form.get('university')
        user.is_admin = 'is_admin' in request.form
        
        db.session.commit()
        flash('User updated successfully', 'success')
        return redirect(url_for('admin_users'))
    
    return render_template('admin/user_detail.html', user=user)

# Assign vendor role to user
@app.route('/admin/users/<int:user_id>/assign_vendor', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_assign_vendor(user_id):
    user = User.query.get_or_404(user_id)
    vendors = Vendor.query.filter_by(status='active').all()
    
    if request.method == 'POST':
        vendor_id = request.form.get('vendor_id')
        
        if vendor_id:
            vendor = Vendor.query.get(vendor_id)
            if vendor:
                user.vendor_id = vendor.id
                db.session.commit()
                flash(f'{user.username} has been assigned to {vendor.name}', 'success')
                return redirect(url_for('admin_user_detail', user_id=user.id))
        else:
            # Remove vendor role
            user.vendor_id = None
            db.session.commit()
            flash(f'Vendor role removed from {user.username}', 'success')
            return redirect(url_for('admin_user_detail', user_id=user.id))
    
    return render_template('admin/assign_vendor.html', user=user, vendors=vendors)

# Admin Delete User
@app.route('/admin/users/delete/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def admin_delete_user(user_id):
    user = User.query.get_or_404(user_id)
    
    if user.id == current_user.id:
        flash('You cannot delete yourself!', 'danger')
        return redirect(url_for('admin_users'))
    
    db.session.delete(user)
    db.session.commit()
    
    flash('User deleted successfully', 'success')
    return redirect(url_for('admin_users'))

# Admin Vendors Management
@app.route('/admin/vendors')
@login_required
@admin_required
def admin_vendors():
    page = request.args.get('page', 1, type=int)
    per_page = 10
    
    vendors = Vendor.query.paginate(page=page, per_page=per_page, error_out=False)
    
    return render_template('admin/vendors.html', vendors=vendors)

# Admin Vendor Add/Edit
@app.route('/admin/vendors/add', methods=['GET', 'POST'])
@app.route('/admin/vendors/edit/<int:vendor_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_vendor_edit(vendor_id=None):
    vendor = None
    if vendor_id:
        vendor = Vendor.query.get_or_404(vendor_id)
        
    if request.method == 'POST':
        if vendor:
            # Update existing vendor
            vendor.name = request.form.get('name')
            vendor.contact_name = request.form.get('contact_name')
            vendor.email = request.form.get('email')
            vendor.phone = request.form.get('phone')
            vendor.address = request.form.get('address')
            vendor.status = request.form.get('status')
        else:
            # Create new vendor
            new_vendor = Vendor(
                name=request.form.get('name'),
                contact_name=request.form.get('contact_name'),
                email=request.form.get('email'),
                phone=request.form.get('phone'),
                address=request.form.get('address'),
                status=request.form.get('status', 'active')
            )
            db.session.add(new_vendor)
            
        db.session.commit()
        flash('Vendor saved successfully', 'success')
        return redirect(url_for('admin_vendors'))
    
    return render_template('admin/vendor_form.html', vendor=vendor)

# Admin Delete Vendor
@app.route('/admin/vendors/delete/<int:vendor_id>', methods=['POST'])
@login_required
@admin_required
def admin_delete_vendor(vendor_id):
    vendor = Vendor.query.get_or_404(vendor_id)
    
    db.session.delete(vendor)
    db.session.commit()
    
    flash('Vendor deleted successfully', 'success')
    return redirect(url_for('admin_vendors'))

# Admin Products Management
@app.route('/admin/products')
@login_required
@admin_required
def admin_products():
    page = request.args.get('page', 1, type=int)
    per_page = 10
    category_filter = request.args.get('category')
    
    # Get all categories for the filter buttons
    categories = Category.query.all()
    
    # Apply category filter if provided
    if category_filter:
        products = Product.query.filter_by(category_id=category_filter).order_by(Product.id.desc())
    else:
        products = Product.query.order_by(Product.id.desc())
    
    # Paginate results
    products = products.paginate(page=page, per_page=per_page, error_out=False)
    
    return render_template('admin/products.html', products=products, categories=categories)

# Admin Product Add/Edit
@app.route('/admin/products/add', methods=['GET', 'POST'])
@app.route('/admin/products/edit/<int:product_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_product_edit(product_id=None):
    product = None
    if product_id:
        product = Product.query.get_or_404(product_id)
    
    categories = Category.query.all()
    vendors = Vendor.query.filter_by(status='active').all()
    
    if request.method == 'POST':
        if product:
            # Update existing product
            product.name = request.form.get('name')
            product.description = request.form.get('description')
            product.price = float(request.form.get('price'))
            product.image_url = request.form.get('image_url')
            product.is_available = 'is_available' in request.form
            product.category_id = int(request.form.get('category_id'))
            product.vendor_id = int(request.form.get('vendor_id')) if request.form.get('vendor_id') else None
        else:
            # Create new product
            new_product = Product(
                name=request.form.get('name'),
                description=request.form.get('description'),
                price=float(request.form.get('price')),
                image_url=request.form.get('image_url'),
                is_available='is_available' in request.form,
                category_id=int(request.form.get('category_id')),
                vendor_id=int(request.form.get('vendor_id')) if request.form.get('vendor_id') else None
            )
            db.session.add(new_product)
            
        db.session.commit()
        flash('Product saved successfully', 'success')
        return redirect(url_for('admin_products'))
    
    return render_template('admin/product_form.html', product=product, categories=categories, vendors=vendors)

# Admin Delete Product
@app.route('/admin/products/delete/<int:product_id>', methods=['POST'])
@login_required
@admin_required
def admin_delete_product(product_id):
    product = Product.query.get_or_404(product_id)
    
    db.session.delete(product)
    db.session.commit()
    
    flash('Product deleted successfully', 'success')
    return redirect(url_for('admin_products'))

# Admin Orders Management
@app.route('/admin/orders')
@login_required
@admin_required
def admin_orders():
    page = request.args.get('page', 1, type=int)
    per_page = 10
    status_filter = request.args.get('status')
    
    # Apply status filter if provided
    if status_filter:
        orders = Order.query.filter_by(status=status_filter).order_by(Order.order_date.desc())
    else:
        orders = Order.query.order_by(Order.order_date.desc())
    
    # Paginate results
    orders = orders.paginate(page=page, per_page=per_page, error_out=False)
    
    return render_template('admin/orders.html', orders=orders)

# Admin Order Detail
@app.route('/admin/orders/<int:order_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_order_detail(order_id):
    order = Order.query.get_or_404(order_id)
    
    if request.method == 'POST':
        order.status = request.form.get('status')
        db.session.commit()
        flash('Order status updated successfully', 'success')
        return redirect(url_for('admin_orders'))
    
    return render_template('admin/order_detail.html', order=order)

# Vendor Dashboard
@app.route('/vendor')
@login_required
@vendor_required
def vendor_dashboard():
    # Get vendor information
    vendor = current_user.vendor
    
    # Get counts for dashboard
    product_count = Product.query.filter_by(vendor_id=vendor.id).count()
    
    # Get orders containing this vendor's products
    vendor_product_ids = [p.id for p in vendor.products]
    
    # Find orders containing vendor's products
    vendor_order_ids = db.session.query(OrderItem.order_id).filter(
        OrderItem.product_id.in_(vendor_product_ids)
    ).distinct().all()
    vendor_order_ids = [id[0] for id in vendor_order_ids]
    
    order_count = len(vendor_order_ids)
    pending_count = Order.query.filter(Order.id.in_(vendor_order_ids), Order.vendor_status == 'pending').count()
    
    # Calculate total revenue from this vendor's products
    total_revenue = db.session.query(db.func.sum(OrderItem.price * OrderItem.quantity)).filter(
        OrderItem.product_id.in_(vendor_product_ids),
        OrderItem.order_id.in_(vendor_order_ids)
    ).scalar() or 0
    
    # Get monthly revenue data for chart
    current_year = datetime.datetime.now().year
    monthly_revenue = []
    
    for month in range(1, 13):
        start_date = datetime.datetime(current_year, month, 1)
        if month == 12:
            end_date = datetime.datetime(current_year + 1, 1, 1) - datetime.timedelta(days=1)
        else:
            end_date = datetime.datetime(current_year, month + 1, 1) - datetime.timedelta(days=1)
        
        month_orders = Order.query.filter(
            Order.id.in_(vendor_order_ids),
            Order.order_date >= start_date,
            Order.order_date <= end_date
        ).all()
        
        month_revenue = 0
        for order in month_orders:
            for item in order.items:
                if item.product_id in vendor_product_ids:
                    month_revenue += item.price * item.quantity
        
        monthly_revenue.append(float(month_revenue))
    
    # Get order status counts for chart
    accepted_count = Order.query.filter(Order.id.in_(vendor_order_ids), Order.vendor_status == 'accepted').count()
    rejected_count = Order.query.filter(Order.id.in_(vendor_order_ids), Order.vendor_status == 'rejected').count()
    order_status_counts = [pending_count, accepted_count, rejected_count]
    
    # Get recent orders
    recent_orders = Order.query.filter(
        Order.id.in_(vendor_order_ids)
    ).order_by(Order.order_date.desc()).limit(5).all()
    
    return render_template('vendor/dashboard.html',
                          vendor=vendor,
                          product_count=product_count,
                          order_count=order_count,
                          pending_count=pending_count,
                          total_revenue=total_revenue,
                          recent_orders=recent_orders,
                          monthly_revenue=monthly_revenue,
                          order_status_counts=order_status_counts,
                          now=datetime.datetime.now())

# Vendor Products Management
@app.route('/vendor/products')
@login_required
@vendor_required
def vendor_products():
    vendor = current_user.vendor
    page = request.args.get('page', 1, type=int)
    per_page = 10
    category_filter = request.args.get('category')
    
    # Get all categories for the filter buttons
    categories = Category.query.all()
    
    # Apply category filter if provided
    if category_filter:
        products = Product.query.filter_by(vendor_id=vendor.id, category_id=category_filter).order_by(Product.id.desc())
    else:
        products = Product.query.filter_by(vendor_id=vendor.id).order_by(Product.id.desc())
    
    # Paginate results
    products = products.paginate(page=page, per_page=per_page, error_out=False)
    
    return render_template('vendor/products.html', products=products, categories=categories)

# Vendor Product Add/Edit
@app.route('/vendor/products/add', methods=['GET', 'POST'])
@app.route('/vendor/products/edit/<int:product_id>', methods=['GET', 'POST'])
@login_required
@vendor_required
def vendor_product_edit(product_id=None):
    vendor = current_user.vendor
    product = None
    
    if product_id:
        product = Product.query.get_or_404(product_id)
        # Ensure vendor only edits their own products
        if product.vendor_id != vendor.id:
            flash('You do not have permission to edit this product', 'danger')
            return redirect(url_for('vendor_products'))
    
    categories = Category.query.all()
    
    if request.method == 'POST':
        if product:
            # Update existing product
            product.name = request.form.get('name')
            product.description = request.form.get('description')
            product.price = float(request.form.get('price'))
            product.image_url = request.form.get('image_url')
            product.is_available = 'is_available' in request.form
            product.category_id = int(request.form.get('category_id'))
        else:
            # Create new product
            new_product = Product(
                name=request.form.get('name'),
                description=request.form.get('description'),
                price=float(request.form.get('price')),
                image_url=request.form.get('image_url'),
                is_available='is_available' in request.form,
                category_id=int(request.form.get('category_id')),
                vendor_id=vendor.id
            )
            db.session.add(new_product)
            
        db.session.commit()
        flash('Product saved successfully', 'success')
        return redirect(url_for('vendor_products'))
    
    return render_template('vendor/product_form.html', product=product, categories=categories)

# Vendor Delete Product
@app.route('/vendor/products/delete/<int:product_id>', methods=['POST'])
@login_required
@vendor_required
def vendor_delete_product(product_id):
    vendor = current_user.vendor
    product = Product.query.get_or_404(product_id)
    
    # Ensure vendor only deletes their own products
    if product.vendor_id != vendor.id:
        flash('You do not have permission to delete this product', 'danger')
        return redirect(url_for('vendor_products'))
    
    db.session.delete(product)
    db.session.commit()
    
    flash('Product deleted successfully', 'success')
    return redirect(url_for('vendor_products'))

# Vendor Orders Management
@app.route('/vendor/orders')
@login_required
@vendor_required
def vendor_orders():
    vendor = current_user.vendor
    page = request.args.get('page', 1, type=int)
    per_page = 10
    status_filter = request.args.get('status')
    
    # Get vendor product IDs
    vendor_product_ids = [p.id for p in vendor.products]
    
    # Find orders containing vendor's products
    vendor_order_ids = db.session.query(OrderItem.order_id).filter(
        OrderItem.product_id.in_(vendor_product_ids)
    ).distinct().all()
    vendor_order_ids = [id[0] for id in vendor_order_ids]
    
    # Apply status filter if provided
    if status_filter:
        orders = Order.query.filter(
            Order.id.in_(vendor_order_ids), 
            Order.vendor_status == status_filter
        ).order_by(Order.order_date.desc())
    else:
        orders = Order.query.filter(
            Order.id.in_(vendor_order_ids)
        ).order_by(Order.order_date.desc())
    
    # Paginate results
    orders = orders.paginate(page=page, per_page=per_page, error_out=False)
    
    return render_template('vendor/orders.html', orders=orders)

# Vendor Order Detail
@app.route('/vendor/orders/<int:order_id>')
@login_required
@vendor_required
def vendor_order_detail(order_id):
    vendor = current_user.vendor
    order = Order.query.get_or_404(order_id)
    
    # Get vendor product IDs
    vendor_product_ids = [p.id for p in vendor.products]
    
    # Check if order contains vendor's products
    order_contains_vendor_products = False
    for item in order.items:
        if item.product_id in vendor_product_ids:
            order_contains_vendor_products = True
            break
    
    if not order_contains_vendor_products:
        flash('You do not have permission to view this order', 'danger')
        return redirect(url_for('vendor_orders'))
    
    return render_template('vendor/order_detail.html', order=order)

# Vendor Accept Order
@app.route('/vendor/orders/<int:order_id>/accept', methods=['POST'])
@login_required
@vendor_required
def vendor_accept_order(order_id):
    vendor = current_user.vendor
    order = Order.query.get_or_404(order_id)
    
    # Get vendor product IDs
    vendor_product_ids = [p.id for p in vendor.products]
    
    # Check if order contains vendor's products
    order_contains_vendor_products = False
    for item in order.items:
        if item.product_id in vendor_product_ids:
            order_contains_vendor_products = True
            break
    
    if not order_contains_vendor_products:
        flash('You do not have permission to update this order', 'danger')
        return redirect(url_for('vendor_orders'))
    
    order.vendor_status = 'accepted'
    db.session.commit()
    
    flash('Order accepted successfully', 'success')
    return redirect(url_for('vendor_order_detail', order_id=order.id))

# Vendor Reject Order
@app.route('/vendor/orders/<int:order_id>/reject', methods=['POST'])
@login_required
@vendor_required
def vendor_reject_order(order_id):
    vendor = current_user.vendor
    order = Order.query.get_or_404(order_id)
    
    # Get vendor product IDs
    vendor_product_ids = [p.id for p in vendor.products]
    
    # Check if order contains vendor's products
    order_contains_vendor_products = False
    for item in order.items:
        if item.product_id in vendor_product_ids:
            order_contains_vendor_products = True
            break
    
    if not order_contains_vendor_products:
        flash('You do not have permission to update this order', 'danger')
        return redirect(url_for('vendor_orders'))
    
    order.vendor_status = 'rejected'
    db.session.commit()
    
    flash('Order rejected successfully', 'success')
    return redirect(url_for('vendor_order_detail', order_id=order.id))

# Vendor Settings
@app.route('/vendor/settings', methods=['GET', 'POST'])
@login_required
@vendor_required
def vendor_settings():
    vendor = current_user.vendor
    
    if request.method == 'POST':
        vendor.name = request.form.get('name')
        vendor.contact_name = request.form.get('contact_name')
        vendor.email = request.form.get('email')
        vendor.phone = request.form.get('phone')
        vendor.address = request.form.get('address')
        
        db.session.commit()
        flash('Shop information updated successfully', 'success')
        return redirect(url_for('vendor_settings'))
    
    return render_template('vendor/settings.html', vendor=vendor)

# Vendor Update Description
@app.route('/vendor/description', methods=['POST'])
@login_required
@vendor_required
def vendor_update_description():
    vendor = current_user.vendor
    
    vendor.description = request.form.get('description')
    db.session.commit()
    
    flash('Shop description updated successfully', 'success')
    return redirect(url_for('vendor_settings'))

# Vendor Deactivate Shop
@app.route('/vendor/deactivate', methods=['POST'])
@login_required
@vendor_required
def vendor_deactivate():
    vendor = current_user.vendor
    
    vendor.status = 'inactive'
    # Also mark all products as unavailable
    for product in vendor.products:
        product.is_available = False
    
    db.session.commit()
    
    flash('Your shop has been temporarily closed', 'success')
    return redirect(url_for('vendor_settings'))

# Vendor Reactivate Shop
@app.route('/vendor/reactivate', methods=['POST'])
@login_required
@vendor_required
def vendor_reactivate():
    vendor = current_user.vendor
    
    vendor.status = 'active'
    db.session.commit()
    
    flash('Your shop has been reopened', 'success')
    return redirect(url_for('vendor_settings'))