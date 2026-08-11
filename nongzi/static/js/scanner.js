// USB 扫码枪输入处理 + Toast通知

function showToast(message, type) {
    type = type || "success";
    var bg = type === "error" ? "bg-danger" : "bg-success";
    var icon = type === "error" ? "fa-exclamation-circle" : "fa-check-circle";
    var toast = document.createElement("div");
    toast.className = "toast align-items-center text-white " + bg + " border-0 position-fixed";
    toast.style.cssText = "top:80px;right:20px;z-index:9999;min-width:200px;";
    toast.setAttribute("role", "alert");
    toast.setAttribute("data-bs-autohide", "true");
    toast.setAttribute("data-bs-delay", "2000");
    toast.innerHTML = '<div class="d-flex"><div class="toast-body"><i class="fas ' + icon + ' me-2"></i>' + message + '</div><button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button></div>';
    document.body.appendChild(toast);
    var bsToast = new bootstrap.Toast(toast);
    bsToast.show();
    toast.addEventListener("hidden.bs.toast", function() { toast.remove(); });
}

var scannerBuffer = "";
var lastKeyTime = 0;
var scannerClearTimer = null;

document.addEventListener("keydown", function(e) {
    // Don't intercept when user is typing in regular text inputs
    var tag = e.target.tagName;
    if (tag === "INPUT" || tag === "TEXTAREA") {
        if (e.target.id === "productSearch" || e.target.classList.contains("scanner-ready")) {
            // pass through
        } else if (e.target.type === "text" || e.target.type === "search" || tag === "TEXTAREA") {
            return;
        }
    }

    var now = Date.now();
    var interval = now - lastKeyTime;

    if (e.key === "Enter" && scannerBuffer.length > 0 && interval < 80) {
        // Scanner completed
        handleBarcodeScan(scannerBuffer.trim());
        scannerBuffer = "";
        e.preventDefault();
        return;
    }

    if (e.key.length === 1 && interval < 80) {
        scannerBuffer += e.key;
    } else if (interval >= 80) {
        scannerBuffer = e.key.length === 1 ? e.key : "";
    }

    lastKeyTime = now;

    // Clear buffer if no enter received within 150ms
    clearTimeout(scannerClearTimer);
    scannerClearTimer = setTimeout(function() {
        scannerBuffer = "";
    }, 150);
});

function handleBarcodeScan(barcode) {
    fetch("/products/api/by-barcode/" + encodeURIComponent(barcode))
        .then(function(r) {
            if (!r.ok) throw new Error("not found");
            return r.json();
        })
        .then(function(product) {
            if (product && typeof addToCart === "function") {
                addToCart(product);
                showToast("已加入: " + product.name, "success");
            } else if (product && document.getElementById("productSearch")) {
                document.getElementById("productSearch").value = barcode;
                document.getElementById("productSearch").dispatchEvent(new Event("input", { bubbles: true }));
            }
        })
        .catch(function() {
            showToast("未找到该条码商品: " + barcode, "error");
        });
}
