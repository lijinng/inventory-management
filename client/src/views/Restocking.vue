<template>
  <div class="restocking">
    <div class="page-header">
      <h2>{{ t('restocking.title') }}</h2>
      <p>{{ t('restocking.description') }}</p>
    </div>

    <div v-if="loading" class="loading">{{ t('common.loading') }}</div>
    <div v-else-if="error" class="error">{{ error }}</div>
    <div v-else>
      <div class="card">
        <div class="card-header">
          <h3 class="card-title">{{ t('restocking.budget') }}</h3>
        </div>
        <div class="slider-row">
          <input
            v-model.number="budget"
            type="range"
            class="budget-slider"
            min="0"
            :max="maxBudget"
            :step="BUDGET_STEP"
            :style="{ '--fill': sliderFill }"
            :aria-label="t('restocking.budget')"
          />
          <div class="slider-scale">
            <span>{{ currencySymbol }}0</span>
            <span>{{ t('restocking.maxBudget') }}: {{ formatMoney(maxBudget) }}</span>
          </div>
        </div>
        <div class="stats-grid summary-grid">
          <div class="stat-card info">
            <div class="stat-label">{{ t('restocking.budget') }}</div>
            <div class="stat-value">{{ formatMoney(budget) }}</div>
          </div>
          <div class="stat-card">
            <div class="stat-label">{{ t('restocking.plannedSpend') }}</div>
            <div class="stat-value">{{ formatMoney(plannedSpend) }}</div>
          </div>
          <div class="stat-card success">
            <div class="stat-label">{{ t('restocking.remaining') }}</div>
            <div class="stat-value">{{ formatMoney(remainingBudget) }}</div>
          </div>
        </div>
      </div>

      <div class="card">
        <div class="card-header">
          <h3 class="card-title">{{ t('restocking.recommendedTitle') }} ({{ recommendation.length }})</h3>
          <button
            class="place-order-btn"
            :disabled="recommendation.length === 0 || submitting"
            @click="placeOrder"
          >
            {{ submitting ? t('restocking.submitting') : t('restocking.placeOrder') }}
          </button>
        </div>

        <div v-if="successMessage" class="inline-message success-message" role="status">{{ successMessage }}</div>
        <div v-if="submitError" class="inline-message error-message" role="alert">{{ submitError }}</div>

        <div v-if="recommendation.length === 0" class="empty-state">{{ t('restocking.noItems') }}</div>
        <div v-else class="table-container">
          <table>
            <thead>
              <tr>
                <th>{{ t('restocking.table.sku') }}</th>
                <th>{{ t('restocking.table.itemName') }}</th>
                <th>{{ t('restocking.table.trend') }}</th>
                <th class="num">{{ t('restocking.table.quantity') }}</th>
                <th class="num">{{ t('restocking.table.unitCost') }}</th>
                <th class="num">{{ t('restocking.table.lineCost') }}</th>
                <th class="num">{{ t('restocking.table.leadTime') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in recommendation" :key="row.item_sku">
                <td><strong>{{ row.item_sku }}</strong></td>
                <td>{{ row.item_name }}</td>
                <td>
                  <span :class="['badge', row.trend]">{{ t(`trends.${row.trend}`) }}</span>
                </td>
                <td class="num">{{ row.quantity }}</td>
                <td class="num">{{ formatMoney(row.unit_cost) }}</td>
                <td class="num"><strong>{{ formatMoney(row.line_cost) }}</strong></td>
                <td class="num">{{ row.lead_time_days }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, computed, onMounted } from 'vue'
import { api } from '../api'
import { useI18n } from '../composables/useI18n'

// Slider granularity in currency units
const BUDGET_STEP = 100

// Lower rank = funded first
const TREND_RANK = { increasing: 0, stable: 1, decreasing: 2 }

export default {
  name: 'Restocking',
  setup() {
    const { t, currentCurrency } = useI18n()
    const currencySymbol = computed(() => (currentCurrency.value === 'JPY' ? '¥' : '$'))

    const loading = ref(true)
    const error = ref(null)
    const forecasts = ref([])
    const budget = ref(0)
    const submitting = ref(false)
    const successMessage = ref('')
    const submitError = ref('')

    // Round to cents to avoid float drift when summing/subtracting costs
    const toCents = (n) => Math.round(n * 100) / 100

    // Items whose forecast exceeds current demand; gap = units we should stock up on.
    // Filters out items with missing/invalid cost data so they cannot break the math.
    const candidates = computed(() =>
      forecasts.value
        .map(f => ({ ...f, gap: f.forecasted_demand - f.current_demand }))
        .filter(f => f.gap > 0 && Number.isFinite(f.unit_cost) && f.unit_cost > 0)
    )

    // Slider max: cost of fully covering every positive gap, rounded up to the step
    const maxBudget = computed(() => {
      const total = candidates.value.reduce((sum, f) => sum + f.gap * f.unit_cost, 0)
      return Math.ceil(total / BUDGET_STEP) * BUDGET_STEP
    })

    // Greedy recommendation. Rank by trend (increasing items are most likely to
    // run short, then stable, then decreasing), breaking ties by larger gap first.
    // Walk the ranked list once, buying as many units as the remaining budget allows
    // (capped at the gap) and skipping items where not even one unit is affordable.
    // A skipped expensive item does not stop cheaper, lower-ranked items from being funded.
    const recommendation = computed(() => {
      const ranked = [...candidates.value].sort((a, b) => {
        const rankDiff = (TREND_RANK[a.trend] ?? 3) - (TREND_RANK[b.trend] ?? 3)
        return rankDiff !== 0 ? rankDiff : b.gap - a.gap
      })

      let remaining = budget.value
      const rows = []
      for (const f of ranked) {
        const quantity = Math.min(f.gap, Math.floor(remaining / f.unit_cost))
        if (quantity <= 0) continue
        const lineCost = toCents(quantity * f.unit_cost)
        remaining = toCents(remaining - lineCost)
        rows.push({
          item_sku: f.item_sku,
          item_name: f.item_name,
          trend: f.trend,
          quantity,
          unit_cost: f.unit_cost,
          line_cost: lineCost,
          lead_time_days: f.lead_time_days
        })
      }
      return rows
    })

    const plannedSpend = computed(() =>
      toCents(recommendation.value.reduce((sum, r) => sum + r.line_cost, 0))
    )
    const remainingBudget = computed(() => toCents(budget.value - plannedSpend.value))

    // Percentage of the track to paint blue on the slider
    const sliderFill = computed(() =>
      maxBudget.value > 0 ? `${(budget.value / maxBudget.value) * 100}%` : '0%'
    )

    const formatMoney = (value) =>
      `${currencySymbol.value}${Number(value).toLocaleString(undefined, { maximumFractionDigits: 2 })}`

    const loadData = async () => {
      try {
        loading.value = true
        error.value = null
        forecasts.value = await api.getDemandForecasts()
        // Start at half of the maximum so the recommendation is visibly budget-constrained
        budget.value = Math.round(maxBudget.value / 2 / BUDGET_STEP) * BUDGET_STEP
      } catch (err) {
        error.value = t('restocking.loadFailure') + ': ' + err.message
      } finally {
        loading.value = false
      }
    }

    const placeOrder = async () => {
      if (recommendation.value.length === 0 || submitting.value) return
      submitting.value = true
      successMessage.value = ''
      submitError.value = ''
      try {
        const order = await api.createRestockingOrder({
          items: recommendation.value.map(r => ({ item_sku: r.item_sku, quantity: r.quantity })),
          budget: budget.value
        })
        successMessage.value = t('restocking.success', {
          orderNumber: order.order_number,
          days: order.lead_time_days
        })
      } catch (err) {
        submitError.value = err.response?.data?.detail || t('restocking.failure')
      } finally {
        submitting.value = false
      }
    }

    onMounted(loadData)

    return {
      t,
      BUDGET_STEP,
      currencySymbol,
      loading,
      error,
      budget,
      maxBudget,
      recommendation,
      plannedSpend,
      remainingBudget,
      sliderFill,
      submitting,
      successMessage,
      submitError,
      formatMoney,
      placeOrder
    }
  }
}
</script>

<style scoped>
.slider-row {
  margin-bottom: 1.25rem;
}

.budget-slider {
  -webkit-appearance: none;
  appearance: none;
  width: 100%;
  height: 8px;
  border-radius: 4px;
  outline: none;
  cursor: pointer;
  background: linear-gradient(to right, #2563eb 0, #2563eb var(--fill, 0%), #e2e8f0 var(--fill, 0%), #e2e8f0 100%);
}

.budget-slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: #ffffff;
  border: 2px solid #2563eb;
  box-shadow: 0 1px 3px rgba(15, 23, 42, 0.2);
  transition: box-shadow 0.15s ease;
}

.budget-slider::-moz-range-thumb {
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: #ffffff;
  border: 2px solid #2563eb;
  box-shadow: 0 1px 3px rgba(15, 23, 42, 0.2);
}

.budget-slider:focus-visible::-webkit-slider-thumb {
  box-shadow: 0 0 0 4px rgba(37, 99, 235, 0.25);
}

.budget-slider:focus-visible::-moz-range-thumb {
  box-shadow: 0 0 0 4px rgba(37, 99, 235, 0.25);
}

.slider-scale {
  display: flex;
  justify-content: space-between;
  margin-top: 0.5rem;
  font-size: 0.813rem;
  color: #64748b;
}

.summary-grid {
  margin-bottom: 0;
}

.summary-grid .stat-value {
  font-size: 1.75rem;
}

.place-order-btn {
  padding: 0.5rem 1.25rem;
  background: #2563eb;
  color: #ffffff;
  border: none;
  border-radius: 6px;
  font-size: 0.875rem;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.15s ease;
}

.place-order-btn:hover:not(:disabled) {
  background: #1d4ed8;
}

.place-order-btn:disabled {
  background: #cbd5e1;
  color: #64748b;
  cursor: not-allowed;
}

.inline-message {
  padding: 0.75rem 1rem;
  border-radius: 8px;
  margin-bottom: 1rem;
  font-size: 0.875rem;
}

.success-message {
  background: #ecfdf5;
  border: 1px solid #a7f3d0;
  color: #065f46;
}

.error-message {
  background: #fef2f2;
  border: 1px solid #fecaca;
  color: #991b1b;
}

.empty-state {
  text-align: center;
  padding: 2rem;
  color: #64748b;
  font-size: 0.938rem;
}

.num {
  text-align: right;
}
</style>
