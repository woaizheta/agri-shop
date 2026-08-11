// 购物车逻辑 (sessionStorage)

const CART_KEY = 'agrishop_cart';

function getCart() {
    try {
        return JSON.parse(sessionStorage.getItem(CART_KEY) || '[]');
    } catch(e) {
        return [];
    }
}

function saveCart(cart) {
    sessionStorage.setItem(CART_KEY, JSON.stringify(cart));
}

function clearCart() {
    sessionStorage.removeItem(CART_KEY);
}

function addToCartItem(productId, name, spec, quantity, unitPrice, baseUnit) {
    let cart = getCart();
    let found = cart.find(item => item.productId === productId);
    if (found) {
        found.quantity += quantity;
    } else {
        cart.push({
            productId: productId,
            name: name,
            spec: spec || '',
            quantity: quantity,
            unitPrice: unitPrice,
            baseUnit: baseUnit
        });
    }
    saveCart(cart);
    return cart;
}

function removeFromCart(index) {
    let cart = getCart();
    cart.splice(index, 1);
    saveCart(cart);
    return cart;
}

function updateCartItem(index, quantity) {
    let cart = getCart();
    cart[index].quantity = parseFloat(quantity) || 0;
    if (cart[index].quantity <= 0) {
        cart.splice(index, 1);
    }
    saveCart(cart);
    return cart;
}

function cartTotal() {
    return getCart().reduce((sum, item) => sum + item.quantity * item.unitPrice, 0);
}
