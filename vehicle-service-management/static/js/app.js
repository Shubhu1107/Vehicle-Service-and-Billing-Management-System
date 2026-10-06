/**
 * AutoCare Pro - Core Client-side Scripts
 */

document.addEventListener('DOMContentLoaded', function () {
  // Mobile Sidebar Toggle
  const toggleBtn = document.getElementById('sidebarToggleBtn');
  const sidebar = document.getElementById('appSidebar');
  if (toggleBtn && sidebar) {
    toggleBtn.addEventListener('click', function () {
      sidebar.classList.toggle('show');
    });

    // Close when clicking outside on mobile
    document.addEventListener('click', function (e) {
      if (window.innerWidth < 992 && !sidebar.contains(e.target) && !toggleBtn.contains(e.target)) {
        sidebar.classList.remove('show');
      }
    });
  }

  // Auto-dismiss alert messages after 5 seconds
  const alertElements = document.querySelectorAll('.alert-dismissible');
  alertElements.forEach(function (alertEl) {
    setTimeout(function () {
      const bsAlert = bootstrap.Alert.getOrCreateInstance(alertEl);
      if (bsAlert) {
        bsAlert.close();
      }
    }, 5000);
  });

  // Dynamic Bill Generator Calculations
  initBillCalculation();
});

/**
 * Initializes and manages dynamic recalculations on the bill generation form.
 */
function initBillCalculation() {
  const billForm = document.getElementById('billGeneratorForm');
  if (!billForm) return;

  const serviceChargeInput = document.getElementById('serviceChargeInput');
  const additionalChargeInput = document.getElementById('additionalChargeInput');
  const discountInput = document.getElementById('discountInput');
  const taxRateInput = document.getElementById('taxRateInput');

  const subtotalDisplay = document.getElementById('subtotalDisplay');
  const taxDisplay = document.getElementById('taxDisplay');
  const grandTotalDisplay = document.getElementById('grandTotalDisplay');

  function calculateTotals() {
    let serviceCharge = parseFloat(serviceChargeInput?.value) || 0;
    let additionalCharge = parseFloat(additionalChargeInput?.value) || 0;
    let discount = parseFloat(discountInput?.value) || 0;
    let taxRate = parseFloat(taxRateInput?.value) || 18.0;

    // Sum all itemized parts rows
    let partsTotal = 0;
    const itemRows = document.querySelectorAll('.item-row');
    itemRows.forEach(row => {
      const qtyInput = row.querySelector('.item-qty');
      const priceInput = row.querySelector('.item-price');
      const rowTotalDisplay = row.querySelector('.item-total-display');

      const qty = parseFloat(qtyInput?.value) || 0;
      const price = parseFloat(priceInput?.value) || 0;
      const rowTotal = qty * price;

      if (rowTotalDisplay) {
        rowTotalDisplay.textContent = '₹ ' + rowTotal.toFixed(2);
      }
      partsTotal += rowTotal;
    });

    const partsTotalInput = document.getElementById('partsChargeInput');
    if (partsTotalInput) {
      partsTotalInput.value = partsTotal.toFixed(2);
    }

    const subtotal = serviceCharge + additionalCharge + partsTotal;
    const taxableAmount = Math.max(0, subtotal - discount);
    const tax = (taxableAmount * taxRate) / 100;
    const grandTotal = taxableAmount + tax;

    if (subtotalDisplay) subtotalDisplay.textContent = '₹ ' + subtotal.toFixed(2);
    if (taxDisplay) taxDisplay.textContent = '₹ ' + tax.toFixed(2);
    if (grandTotalDisplay) grandTotalDisplay.textContent = '₹ ' + grandTotal.toFixed(2);
  }

  // Attach event listeners to inputs
  [serviceChargeInput, additionalChargeInput, discountInput, taxRateInput].forEach(inp => {
    if (inp) inp.addEventListener('input', calculateTotals);
  });

  // Attach dynamic row calculation listeners
  function attachRowEvents(row) {
    const qtyInput = row.querySelector('.item-qty');
    const priceInput = row.querySelector('.item-price');
    const removeBtn = row.querySelector('.btn-remove-row');

    if (qtyInput) qtyInput.addEventListener('input', calculateTotals);
    if (priceInput) priceInput.addEventListener('input', calculateTotals);
    if (removeBtn) {
      removeBtn.addEventListener('click', function () {
        const totalRows = document.querySelectorAll('.item-row').length;
        if (totalRows > 1) {
          row.remove();
          calculateTotals();
        } else {
          // If only 1 row, clear values
          qtyInput.value = '1';
          priceInput.value = '0';
          const nameInput = row.querySelector('input[name="item_name[]"]');
          if (nameInput) nameInput.value = '';
          calculateTotals();
        }
      });
    }
  }

  document.querySelectorAll('.item-row').forEach(attachRowEvents);

  // Add Item Row Button
  const addItemBtn = document.getElementById('addItemRowBtn');
  const itemsContainer = document.getElementById('billItemsContainer');

  if (addItemBtn && itemsContainer) {
    addItemBtn.addEventListener('click', function () {
      const template = `
        <tr class="item-row">
          <td>
            <input type="text" name="item_name[]" class="form-control form-control-sm" placeholder="e.g. Engine Oil Synthetic" required>
          </td>
          <td>
            <input type="text" name="item_description[]" class="form-control form-control-sm" placeholder="OEM Grade or Specs">
          </td>
          <td style="width: 100px;">
            <input type="number" name="item_qty[]" class="form-control form-control-sm item-qty" value="1" min="1" step="1" required>
          </td>
          <td style="width: 140px;">
            <div class="input-group input-group-sm">
              <span class="input-group-text">₹</span>
              <input type="number" name="item_price[]" class="form-control item-price" value="0.00" min="0" step="0.01" required>
            </div>
          </td>
          <td style="width: 120px;" class="text-end fw-semibold item-total-display">
            ₹ 0.00
          </td>
          <td style="width: 50px;" class="text-center">
            <button type="button" class="btn btn-outline-danger btn-sm btn-remove-row">
              <i class="bi bi-trash"></i>
            </button>
          </td>
        </tr>
      `;
      itemsContainer.insertAdjacentHTML('beforeend', template);
      const newRow = itemsContainer.lastElementChild;
      attachRowEvents(newRow);
      calculateTotals();
    });
  }

  // Initial calculation on page load
  calculateTotals();
}

/**
 * Print trigger function
 */
function printDocument() {
  window.print();
}
