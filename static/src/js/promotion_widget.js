/** @odoo-module **/

// Funciones utilitarias para promociones
window.PromotionUtils = {
  /**
   * Calcula descuento para una promoción
   */
  calculateDiscount: function (promotion, price, quantity) {
    quantity = quantity || 1;
    const subtotal = price * quantity;

    if (promotion.discount_type === "percentage") {
      return subtotal * (promotion.discount / 100);
    } else {
      return Math.min(promotion.fixed_discount, subtotal);
    }
  },

  /**
   * Verifica si una promoción es aplicable
   */
  isPromotionApplicable: function (promotion, minimumAmount) {
    minimumAmount = minimumAmount || 0;
    const today = new Date();
    const startDate = new Date(promotion.start_date);
    const endDate = new Date(promotion.end_date);

    return (
      promotion.active &&
      today >= startDate &&
      today <= endDate &&
      (promotion.minimum_amount === 0 ||
        minimumAmount >= promotion.minimum_amount)
    );
  },

  /**
   * Formatea precio con descuento
   */
  formatDiscountedPrice: function (originalPrice, discount) {
    const discountedPrice = originalPrice - discount;
    return {
      original: originalPrice.toFixed(2),
      discounted: discountedPrice.toFixed(2),
      savings: discount.toFixed(2),
    };
  },
};

// Funciones básicas para el frontend
document.addEventListener("DOMContentLoaded", function () {
  // Animaciones básicas para badges de promoción
  const promotionBadges = document.querySelectorAll(".promotion-badge");
  promotionBadges.forEach(function (badge) {
    if (badge.classList.contains("active")) {
      badge.style.animation = "pulse 2s infinite";
    }
  });
});

// CSS para animación de pulse
const style = document.createElement("style");
style.textContent = `
  @keyframes pulse {
      0% { box-shadow: 0 0 0 0 rgba(40, 167, 69, 0.7); }
      70% { box-shadow: 0 0 0 10px rgba(40, 167, 69, 0); }
      100% { box-shadow: 0 0 0 0 rgba(40, 167, 69, 0); }
  }
`;
document.head.appendChild(style);
