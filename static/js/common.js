// Common Select2 initialization helper
// Prevent double initialization of Select2 widgets across the project.
// Usage: initSelect2(selector, options);

function initSelect2(selector, options) {
    const $el = $(selector);
    // If already initialized, Select2 adds the class 'select2-hidden-accessible' to the original <select>
    if ($el.hasClass('select2-hidden-accessible')) {
        return;
    }
    // Ensure options is an object
    const opts = options || {};
    $el.select2(opts);
}

// Optional: safe destroy then init
function destroyAndInitSelect2(selector, options) {
    const $el = $(selector);
    if ($el.hasClass('select2-hidden-accessible')) {
        $el.select2('destroy');
    }
    initSelect2(selector, options);
}

// Expose globally for other scripts
window.initSelect2 = initSelect2;
window.destroyAndInitSelect2 = destroyAndInitSelect2;
