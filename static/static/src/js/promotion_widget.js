/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, useState, onWillStart } from "@odoo/owl";

/**
 * Widget para mostrar promociones en tiempo real
 */
export class PromotionWidget extends Component {
  setup() {
    this.orm = useService("orm");
    this.notification = useService("notification");

    this.state = useState({
      promotions: [],
      loading: false,
      totalDiscount: 0,
    });

    onWillStart(this.loadPromotions);
  }

  /**
   * Carga promociones vigentes
   */
  async loadPromotions() {
    this.state.loading = true;
    try {
      const promotions = await this.orm.searchRead(
        "retail.promotion",
        [
          ["is_valid", "=", true],
          ["active", "=", true],
        ],
        [
          "name",
          "code",
          "discount",
          "fixed_discount",
          "discount_type",
          "days_remaining",
        ]
      );
      this.state.promotions = promotions;
    } catch (error) {
      this.notification.add("Error loading promotions", { type: "danger" });
    } finally {
      this.state.loading = false;
    }
  }

  /**
   * Calcula descuento para un producto
   */
  calculateDiscount(promotion, price, quantity = 1) {
    const subtotal = price * quantity;

    if (promotion.discount_type === "percentage") {
      return subtotal * (promotion.discount / 100);
    } else {
      return Math.min(promotion.fixed_discount, subtotal);
    }
  }

  /**
   * Aplica promoción a producto
   */
  async applyPromotion(promotionId, productId) {
    this.state.loading = true;
    try {
      await this.orm.call("retail.promotion", "apply_to_product", [
        promotionId,
        productId,
      ]);

      this.notification.add("Promotion applied successfully!", {
        type: "success",
      });
      await this.loadPromotions();
    } catch (error) {
      this.notification.add("Error applying promotion", { type: "danger" });
    } finally {
      this.state.loading = false;
    }
  }

  /**
   * Formatea descuento para mostrar
   */
  formatDiscount(promotion) {
    if (promotion.discount_type === "percentage") {
      return `${promotion.discount}%`;
    } else {
      return `$${promotion.fixed_discount}`;
    }
  }

  /**
   * Determina clase CSS según días restantes
   */
  getPromotionClass(daysRemaining) {
    if (daysRemaining <= 3) return "promotion-expiring";
    if (daysRemaining <= 7) return "promotion-warning";
    return "promotion-active";
  }
}

PromotionWidget.template = "retail_promotions.PromotionWidget";

// Registrar el widget
registry.category("view_widgets").add("promotion_widget", PromotionWidget);

/**
 * Campo personalizado para mostrar promociones en formularios
 */
export class PromotionField extends Component {
  setup() {
    this.orm = useService("orm");
    this.state = useState({
      bestPromotion: null,
      savings: 0,
    });

    onWillStart(this.loadBestPromotion);
  }

  async loadBestPromotion() {
    if (!this.props.record.data.id) return;

    try {
      const result = await this.orm.call(
        "product.template",
        "get_best_promotion",
        [this.props.record.data.id]
      );

      if (result) {
        this.state.bestPromotion = result;
        this.state.savings = this.calculateSavings(result);
      }
    } catch (error) {
      console.error("Error loading best promotion:", error);
    }
  }

  calculateSavings(promotion) {
    const price = this.props.record.data.list_price || 0;

    if (promotion.discount_type === "percentage") {
      return price * (promotion.discount / 100);
    } else {
      return Math.min(promotion.fixed_discount, price);
    }
  }
}

PromotionField.template = "retail_promotions.PromotionField";
registry.category("fields").add("promotion_field", PromotionField);

/**
 * Funciones utilitarias para promociones
 */
export const PromotionUtils = {
  /**
   * Calcula el mejor descuento entre múltiples promociones
   */
  getBestDiscount(promotions, price, quantity = 1) {
    let bestDiscount = 0;
    let bestPromotion = null;

    promotions.forEach((promotion) => {
      const discount = this.calculateDiscount(promotion, price, quantity);
      if (discount > bestDiscount) {
        bestDiscount = discount;
        bestPromotion = promotion;
      }
    });

    return { promotion: bestPromotion, discount: bestDiscount };
  },

  /**
   * Verifica si una promoción es aplicable
   */
  isPromotionApplicable(promotion, minimumAmount = 0) {
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
  formatDiscountedPrice(originalPrice, discount) {
    const discountedPrice = originalPrice - discount;
    return {
      original: originalPrice.toFixed(2),
      discounted: discountedPrice.toFixed(2),
      savings: discount.toFixed(2),
    };
  },
};

// Exportar utilidades globalmente
window.PromotionUtils = PromotionUtils;
