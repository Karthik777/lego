// The whole calculator. lodash is already on `window._` — ui.py links it from
// static/vendor ahead of this file, so there is nothing to wait for.
(function() {
    const initApp = () => {
        // Surreal-like DOM helper (lightweight jQuery-like API)
        const $ = (sel) => {
            const el = typeof sel === 'string' ? document.querySelector(sel) : sel;
            if (!el) return {
                text: () => $, html: () => $, val: () => null, on: () => $,
                show: () => $, hide: () => $, addClass: () => $, removeClass: () => $,
                append: () => $, empty: () => $, attr: () => $
            };
            return {
                text: (t) => { if (t !== undefined) el.textContent = t; return $; },
                html: (h) => { if (h !== undefined) el.innerHTML = h; return $; },
                val: (v) => { 
                    if (v !== undefined) { if (el) el.value = v; return $; }
                    return el ? el.value : null;
                },
                attr: (name, value) => {
                    if (value !== undefined) { el.setAttribute(name, value); return $; }
                    return el.getAttribute(name);
                },
                on: (evt, fn) => { el.addEventListener(evt, fn); return $; },
                show: () => { el.style.display = ''; return $; },
                hide: () => { el.style.display = 'none'; return $; },
                addClass: (c) => { el.classList.add(c); return $; },
                removeClass: (c) => { el.classList.remove(c); return $; },
                append: (child) => {
                    if (typeof child === 'string') {
                        el.insertAdjacentHTML('beforeend', child);
                    } else if (child) {
                        el.appendChild(child);
                    }
                    return $;
                },
                empty: () => { el.innerHTML = ''; return $; }
            };
        };
        
        const _ = window._;

    // The platform catalogue and the use-case templates, rendered into the page as a
    // JSON script tag by ui.py rather than baked into this file — it is a static asset
    // served with a content-hashed ?v=, and the data is built in python.
    const DATA = JSON.parse(document.getElementById('thrifty-data').textContent);

    // Constants
    const LITELLM_URL = "https://raw.githubusercontent.com/BerriAI/litellm/main/model_prices_and_context_window.json";
    const OPENROUTER_URL = "https://openrouter.ai/api/v1/models";
    const platforms = DATA.platforms;
    const useCases = DATA.useCases;
    
    // State
    let models = {};
    let providers = [];
    let savedScenarios = [];
    let currentPlatformTab = 'agent_frameworks';
    
        // Selectors helper
        const $el = (id) => $('#' + id);
    
    // Pure functions for data processing
    const normalizeProvider = _.flowRight(
        (s) => s.replace(/\b\w/g, l => l.toUpperCase()),
        (s) => s.replace(/-/g, " "),
        (s) => s.replace(/_/g, " ")
    );
    
    const extractProvider = (name, litellmProvider) => {
        if (litellmProvider) return normalizeProvider(litellmProvider);
        if (name.includes("/")) return normalizeProvider(name.split("/")[0]);
        return "Other";
    };
    
    const roundPrice = (price) => Math.round(price * 10000) / 10000;
    
    const hasValidPricing = (model) => model.price_input > 0 || model.price_output > 0;
    
    const shouldSkipModel = (name) => {
        const skipTerms = ['sample', 'ft:', 'ft-', 'finetune'];
        return _.some(skipTerms, term => name.toLowerCase().includes(term));
    };
    
    // Process LiteLLM data using functional patterns
    const processLiteLLMData = (data) => {
        return _(data)
            .toPairs()
            .filter(([name, info]) => info.input_cost_per_token && !shouldSkipModel(name))
            .map(([name, info]) => {
                try {
                    return {
                        key: name,
                        model: {
                            name: info.litellm_model || name,
                            provider: extractProvider(name, info.litellm_provider),
                            context_window: info.max_input_tokens || info.max_tokens || 4096,
                            max_output: info.max_output_tokens || 4096,
                            price_input: roundPrice((info.input_cost_per_token || 0) * 1000000),
                            price_output: roundPrice((info.output_cost_per_token || 0) * 1000000)
                        }
                    };
                } catch (e) {
                    return null;
                }
            })
            .compact()
            .filter((item) => hasValidPricing(item.model))
            .reduce((acc, item) => {
                acc[item.key] = item.model;
                return acc;
            }, {});
    };
    
    // Process OpenRouter data using functional patterns
    const processOpenRouterData = (data) => {
        return _(data.data || [])
            .filter(m => {
                const pricing = m.pricing || {};
                const price_in = (parseFloat(pricing.prompt) || 0) * 1000000;
                const price_out = (parseFloat(pricing.completion) || 0) * 1000000;
                return price_in !== 0 || price_out !== 0;
            })
            .map(m => {
                try {
                    const pricing = m.pricing || {};
                    const model_id = m.id || "";
                    const max_output = (m.top_provider && m.top_provider.max_completion_tokens) || 4096;
                    
                    return {
                        key: model_id,
                        model: {
                            name: m.name || model_id,
                            provider: model_id.includes("/") 
                                ? normalizeProvider(model_id.split("/")[0])
                                : "Other",
                            context_window: m.context_length || 4096,
                            max_output: max_output,
                            price_input: roundPrice((parseFloat(pricing.prompt) || 0) * 1000000),
                            price_output: roundPrice((parseFloat(pricing.completion) || 0) * 1000000)
                        }
                    };
                } catch (e) {
                    return null;
                }
            })
            .compact()
            .reduce((acc, item) => {
                acc[item.key] = item.model;
                return acc;
            }, {});
    };
    
    const getDefaultModels = () => ({
        "gpt-4o": {name: "gpt-4o", provider: "OpenAI", context_window: 128000, max_output: 16384, price_input: 2.5, price_output: 10.0},
        "gpt-4o-mini": {name: "gpt-4o-mini", provider: "OpenAI", context_window: 128000, max_output: 16384, price_input: 0.15, price_output: 0.6},
        "gpt-4-turbo": {name: "gpt-4-turbo", provider: "OpenAI", context_window: 128000, max_output: 4096, price_input: 10.0, price_output: 30.0},
        "gpt-3.5-turbo": {name: "gpt-3.5-turbo", provider: "OpenAI", context_window: 16385, max_output: 4096, price_input: 0.5, price_output: 1.5},
        "claude-3-5-sonnet-20241022": {name: "claude-3-5-sonnet-20241022", provider: "Anthropic", context_window: 200000, max_output: 8192, price_input: 3.0, price_output: 15.0},
        "claude-3-opus-20240229": {name: "claude-3-opus-20240229", provider: "Anthropic", context_window: 200000, max_output: 4096, price_input: 15.0, price_output: 75.0},
        "claude-3-haiku-20240307": {name: "claude-3-haiku-20240307", provider: "Anthropic", context_window: 200000, max_output: 4096, price_input: 0.25, price_output: 1.25},
        "gemini/gemini-1.5-pro": {name: "gemini-1.5-pro", provider: "Google", context_window: 2000000, max_output: 8192, price_input: 1.25, price_output: 5.0},
        "gemini/gemini-1.5-flash": {name: "gemini-1.5-flash", provider: "Google", context_window: 1000000, max_output: 8192, price_input: 0.075, price_output: 0.30}
    });
    
    // Fetch models with fallback chain
    const fetchModels = async () => {
        const tryFetch = async (url, processor) => {
            try {
                const response = await fetch(url);
                if (response.ok) {
                    const data = await response.json();
                    const processed = processor(data);
                    if (_.size(processed) > 0) return processed;
                }
            } catch (e) {
                console.log(`Fetch failed for ${url}`, e);
            }
            return null;
        };
        
        return await tryFetch(LITELLM_URL, processLiteLLMData)
            || await tryFetch(OPENROUTER_URL, processOpenRouterData)
            || getDefaultModels();
    };
    
    // Update providers list
    const updateProviders = () => {
        providers = _(models)
            .values()
            .map('provider')
            .uniq()
            .sortBy()
            .value();
        
        const providerSelect = $el('provider-select');
        if (providerSelect && providers.length > 0) {
            providerSelect.html(providers.map(p => `<option value="${p}">${p}</option>`).join(''));
            updateModels();
        }
    };
    
    // Get form values using functional composition
    const getFormValues = () => ({
        modelId: $el('model-select').val(),
        inputTokens: parseInt($el('input-tokens').val() || 0),
        outputTokens: parseInt($el('output-tokens').val() || 0),
        dailyUsers: parseInt($el('daily-users').val() || 0),
        requestsPerUser: parseFloat($el('requests-per-user').val() || 0),
        iterations: parseInt($el('iterations').val() || 1),
        scale: $el('scale-select').val() || 'startup',
        complexity: $el('complexity-select').val() || 'low'
    });
    
    // Calculation helpers
    const getComplexityMultiplier = _.memoize((complexity) => {
        const multipliers = {'low': 1.0, 'medium': 1.5, 'high': 2.5};
        return multipliers[complexity] || 1.0;
    });
    
    const getScaleDiscount = _.memoize((scale) => {
        const discounts = {'startup': 1.0, 'growth': 0.95, 'scale': 0.90, 'enterprise': 0.85};
        return discounts[scale] || 1.0;
    });
    
    const calculatePlatformCosts = _.memoize((scale) => {
        const baseCosts = {'startup': 50, 'growth': 200, 'scale': 800, 'enterprise': 3000};
        return baseCosts[scale] || 50;
    });
    
    // Calculate costs using pure functions
    const calculateCosts = (model, formValues) => {
        const complexityMultiplier = getComplexityMultiplier(formValues.complexity);
        const scaleDiscount = getScaleDiscount(formValues.scale);
        const effectiveIterations = formValues.iterations * complexityMultiplier;
        
        const inputCost = (formValues.inputTokens * effectiveIterations / 1000000) * model.price_input * scaleDiscount;
        const outputCost = (formValues.outputTokens * effectiveIterations / 1000000) * model.price_output * scaleDiscount;
        const costPerRequest = inputCost + outputCost;
        
        const dailyRequests = formValues.dailyUsers * formValues.requestsPerUser;
        const monthlyRequests = dailyRequests * 30;
        const monthlyCost = costPerRequest * monthlyRequests;
        const platformCost = calculatePlatformCosts(formValues.scale);
        const totalMonthlyCost = monthlyCost + platformCost;
        
        return {
            costPerRequest,
            monthlyCost,
            platformCost,
            totalMonthlyCost,
            monthlyRequests,
            effectiveIterations,
            complexityMultiplier,
            scaleDiscount,
            inputCost,
            outputCost
        };
    };
    
    // Format currency
    const formatCurrency = (amount, decimals = 2) => {
        return '$' + amount.toLocaleString(undefined, {minimumFractionDigits: decimals, maximumFractionDigits: decimals});
    };
    
    // Update UI elements
    const updateModels = () => {
        const provider = $el('provider-select').val();
        if (!provider) return;
        
        const providerModels = _(models)
            .toPairs()
            .filter(([id, m]) => m.provider === provider)
            .value();
        
        const modelSelect = $el('model-select');
        modelSelect.html(providerModels.map(([id, m]) => 
            `<option value="${id}">${m.name}</option>`
        ).join(''));
        
        updateModelSpecs();
    };
    
    const updateModelSpecs = () => {
        const formValues = getFormValues();
        const model = models[formValues.modelId];
        if (!model) return;
        
        $el('input-tokens').val(formValues.inputTokens);
        $el('input-tokens').attr('max', model.context_window);
        $el('output-tokens').val(formValues.outputTokens);
        $el('output-tokens').attr('max', model.max_output);
        
        $el('input-info').text(`Max: ${model.context_window.toLocaleString()} tokens`);
        $el('output-info').text(`Max: ${model.max_output.toLocaleString()} tokens`);
        $el('model-info').text(`$${model.price_input}/1M in, ${model.price_output}/1M out`);
        
        recalculateAll();
    };
    
    const updateDisplay = (costs, model, formValues) => {
        $el('cost-per-request').text(formatCurrency(costs.costPerRequest, 4));
        $el('cost-monthly').text(formatCurrency(costs.monthlyCost));
        $el('cost-total-monthly').text(formatCurrency(costs.totalMonthlyCost));
        
        $el('tco-per-request').text(formatCurrency(costs.costPerRequest, 4));
        $el('tco-monthly').text('$' + Math.round(costs.monthlyCost).toLocaleString());
        $el('tco-platform').text('$' + Math.round(costs.platformCost).toLocaleString());
        $el('tco-total').text('$' + Math.round(costs.totalMonthlyCost).toLocaleString());
        
        const breakdownItems = [
            ['Model', model.name],
            ['Complexity', `${formValues.complexity} (${costs.complexityMultiplier}x overhead)`],
            ['Scale Discount', `${formValues.scale} (${Math.round((1 - costs.scaleDiscount) * 100)}% off)`],
            ['Effective Iterations', `${costs.effectiveIterations.toFixed(1)} (${formValues.iterations} × ${costs.complexityMultiplier})`],
            ['Input Cost/Req', formatCurrency(costs.inputCost, 6)],
            ['Output Cost/Req', formatCurrency(costs.outputCost, 6)],
            ['Tokens/Request', (formValues.inputTokens + formValues.outputTokens).toLocaleString()],
            ['Daily Requests', (formValues.dailyUsers * formValues.requestsPerUser).toLocaleString()],
            ['Monthly Requests', costs.monthlyRequests.toLocaleString()],
            ['LLM Cost/Month', formatCurrency(costs.monthlyCost)],
            ['Platform Cost/Month', formatCurrency(costs.platformCost)],
            ['Total Monthly', formatCurrency(costs.totalMonthlyCost)]
        ];
        
        $el('breakdown').html(
            breakdownItems.map(([label, value]) => 
                `<div class="breakdown-item"><span>${label}</span><span>${value}</span></div>`
            ).join('') + 
            `<div class="breakdown-item" style="font-weight: bold; border-top: 2px solid #e5e7eb;"><span>Total Monthly</span><span>${formatCurrency(costs.totalMonthlyCost)}</span></div>`
        );
    };
    
    const calculate = () => {
        const formValues = getFormValues();
        const model = models[formValues.modelId];
        if (!model) return;
        
        const costs = calculateCosts(model, formValues);
        
        updateDisplay(costs, model, formValues);
        
        window.currentCalc = {
            modelId: formValues.modelId,
            model: model.name,
            provider: model.provider,
            ...formValues,
            ...costs,
            timestamp: new Date().toISOString()
        };
    };
    
    const recalculateAll = _.debounce(() => {
        calculate();
        generateModelComparison();
    }, 100);
    
    // Use case functions
    const getRecommendedModelsForTier = (tier) => {
        const modelList = _(models)
            .toPairs()
            .map(([id, m]) => ({
                id,
                ...m,
                totalCost: m.price_input + m.price_output
            }))
            .filter(m => m.totalCost > 0)
            .sortBy('totalCost')
            .value();
        
        if (modelList.length === 0) return [];
        
        const tierSize = Math.ceil(modelList.length / 3);
        const tierMap = {
            'budget': () => modelList.slice(0, tierSize),
            'balanced': () => modelList.slice(tierSize, tierSize * 2),
            'premium': () => modelList.slice(tierSize * 2)
        };
        
        return (tierMap[tier] || tierMap.budget)();
    };
    
    const applyUseCase = () => {
        const ucId = $el('use-case-select').val();
        const uc = useCases[ucId];
        if (!uc) {
            $el('use-case-info').html('');
            return;
        }
        
        const recommendedModels = getRecommendedModelsForTier(uc.model_tier);
        const tierLabels = { budget: 'Budget-friendly', balanced: 'Balanced', premium: 'Premium' };
        
        $el('use-case-info').html(`
            <div style="background: #eff6ff; border: 1px solid #bfdbfe; border-radius: 8px; padding: 12px; font-size: 0.9em;">
                <div style="font-weight: 500; color: #1e40af; margin-bottom: 8px;">${uc.name}</div>
                <div style="color: #64748b; margin-bottom: 8px;">${uc.description}</div>
                <div style="display: flex; flex-wrap: wrap; gap: 8px;">
                    <span class="tag tag-blue">~${uc.typical_input_tokens} input tokens</span>
                    <span class="tag tag-blue">~${uc.typical_output_tokens} output tokens</span>
                    <span class="tag tag-purple">${uc.requests_per_user_day} req/user/day</span>
                    <span class="tag tag-orange">${uc.complexity} complexity</span>
                    <span class="tag tag-green">${tierLabels[uc.model_tier] || uc.model_tier} tier</span>
                </div>
                <div style="margin-top: 8px; font-size: 0.85em; color: #64748b;">
                    <strong>Suggested models:</strong> ${recommendedModels.slice(0, 5).map(m => m.name).join(', ')}
                </div>
            </div>
        `);
        
        $el('input-tokens').val(uc.typical_input_tokens);
        $el('output-tokens').val(uc.typical_output_tokens);
        $el('requests-per-user').val(uc.requests_per_user_day);
        $el('complexity-select').val(uc.complexity);
        
        if (recommendedModels.length > 0) {
            const bestModel = recommendedModels[0];
            $el('provider-select').val(bestModel.provider);
            updateModels();
            $el('model-select').val(bestModel.id);
            updateModelSpecs();
        } else {
            recalculateAll();
        }
        
        updateRecommendations();
    };
    
    const calculateUseCaseCost = (uc) => {
        return _(models)
            .values()
            .map(m => (uc.typical_input_tokens / 1000000) * m.price_input + 
                      (uc.typical_output_tokens / 1000000) * m.price_output)
            .min() || 0;
    };
    
    const renderUseCaseTemplates = () => {
        const complexityColors = {
            'low': { bg: '#d1fae5', text: '#065f46' },
            'medium': { bg: '#fef3c7', text: '#92400e' },
            'high': { bg: '#fee2e2', text: '#991b1b' }
        };
        
        const tierColors = {
            'budget': { bg: '#dbeafe', text: '#1e40af' },
            'balanced': { bg: '#e9d5ff', text: '#6b21a8' },
            'premium': { bg: '#fce7f3', text: '#9d174d' }
        };
        
        const tierLabels = { budget: 'Budget', balanced: 'Balanced', premium: 'Premium' };
        
        const templateHtml = _(useCases)
            .toPairs()
            .map(([id, uc]) => {
                const colors = complexityColors[uc.complexity] || complexityColors.low;
                const tColors = tierColors[uc.model_tier] || tierColors.budget;
                const estimatedCost = formatCurrency(calculateUseCaseCost(uc), 4);
                
                return `
                    <div class="scenario-card" onclick="selectUseCaseTemplate('${id}')" style="cursor: pointer;">
                        <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 8px;">
                            <h4 style="margin: 0; font-size: 1em;">${uc.name}</h4>
                            <div>
                                <span class="tag" style="background: ${colors.bg}; color: ${colors.text};">${uc.complexity}</span>
                                <span class="tag" style="background: ${tColors.bg}; color: ${tColors.text};">${tierLabels[uc.model_tier] || uc.model_tier}</span>
                            </div>
                        </div>
                        <p style="margin: 0 0 10px 0; color: #64748b; font-size: 0.85em;">${uc.description}</p>
                        <div style="display: flex; flex-wrap: wrap; gap: 4px; margin-bottom: 8px;">
                            <span class="tag tag-gray">${uc.typical_input_tokens} in</span>
                            <span class="tag tag-gray">${uc.typical_output_tokens} out</span>
                            <span class="tag tag-gray">${uc.requests_per_user_day} req/day</span>
                        </div>
                        <div style="font-size: 0.85em; color: #2563eb; font-weight: 500;">
                            Est. ${estimatedCost}/request (cheapest model)
                        </div>
                    </div>
                `;
            })
            .value()
            .join('');
        
        $el('use-case-templates-grid').html(`<div class="grid-3" style="grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));">${templateHtml}</div>`);
    };
    
    const selectUseCaseTemplate = (ucId) => {
        $el('use-case-select').val(ucId);
        applyUseCase();
        document.querySelector('.card')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    };
    
    // Platform recommendations
    const showPlatformTab = (category) => {
        currentPlatformTab = category;
        const formValues = getFormValues();
        const scale = formValues.scale;
        const complexity = formValues.complexity;
        
        document.querySelectorAll('.section-tab').forEach(tab => tab.classList.remove('active'));
        event?.target?.classList.add('active');
        
        const categoryPlatforms = platforms[category] || {};
        
        const platformHtml = _(categoryPlatforms)
            .toPairs()
            .map(([key, p]) => {
                const isRecommended = p.scale_fit.includes(scale) && p.complexity_fit.includes(complexity);
                const borderColor = isRecommended ? '#22c55e' : '#e2e8f0';
                
                return `
                    <div class="platform-card" style="border-color: ${borderColor}; ${isRecommended ? 'border-width: 2px;' : ''}">
                        <div style="display: flex; justify-content: space-between; align-items: start;">
                            <h4>${p.name}</h4>
                            ${isRecommended ? '<span class="tag tag-green">Recommended</span>' : ''}
                        </div>
                        <p>${p.description}</p>
                        <div style="margin-bottom: 10px;">
                            <span class="tag tag-blue">${p.pricing_model}</span>
                            ${p.estimated_monthly_base > 0 ? `<span class="tag tag-orange">~$${p.estimated_monthly_base}/mo base</span>` : ''}
                        </div>
                        <div class="pros-cons">
                            <div>
                                <strong style="color: #059669; font-size: 0.85em;">Pros:</strong>
                                <ul class="pros">${p.pros.map(pro => `<li>${pro}</li>`).join('')}</ul>
                            </div>
                            <div>
                                <strong style="color: #dc2626; font-size: 0.85em;">Cons:</strong>
                                <ul class="cons">${p.cons.map(con => `<li>${con}</li>`).join('')}</ul>
                            </div>
                        </div>
                        <div style="margin-top: 10px;">
                            <strong style="font-size: 0.85em;">Best for:</strong>
                            <div>${p.best_for.map(b => `<span class="tag tag-gray">${b}</span>`).join('')}</div>
                        </div>
                        ${p.url ? `<a href="${p.url}" target="_blank" style="display: inline-block; margin-top: 10px; font-size: 0.85em; color: #2563eb;">Learn more →</a>` : ''}
                    </div>
                `;
            })
            .value()
            .join('');
        
        $el('platform-recommendations').html(`<div class="grid-2">${platformHtml}</div>`);
    };
    
    const updateRecommendations = () => {
        showPlatformTab(currentPlatformTab);
        recalculateAll();
    };
    
    // Model comparison
    const generateModelComparison = () => {
        const formValues = getFormValues();
        const currentModelId = formValues.modelId;
        
        const complexityMultiplier = getComplexityMultiplier(formValues.complexity);
        const scaleDiscount = getScaleDiscount(formValues.scale);
        const effectiveIterations = formValues.iterations * complexityMultiplier;
        const monthlyRequests = formValues.dailyUsers * formValues.requestsPerUser * 30;
        
        const modelCosts = _(models)
            .toPairs()
            .map(([id, m]) => {
                const inputCost = (formValues.inputTokens * effectiveIterations / 1000000) * m.price_input * scaleDiscount;
                const outputCost = (formValues.outputTokens * effectiveIterations / 1000000) * m.price_output * scaleDiscount;
                const costPerRequest = inputCost + outputCost;
                const monthlyCost = costPerRequest * monthlyRequests;
                
                return {
                    id,
                    name: m.name,
                    provider: m.provider,
                    costPerRequest,
                    monthlyCost,
                    contextWindow: m.context_window,
                    isCurrent: id === currentModelId
                };
            })
            .sortBy('monthlyCost')
            .value();
        
        const currentModelCost = _.find(modelCosts, m => m.isCurrent);
        const cheapestModel = modelCosts[0];
        const currentRank = _.findIndex(modelCosts, m => m.isCurrent) + 1;
        
        let html = '';
        
        if (currentModelCost && cheapestModel) {
            const savings = currentModelCost.monthlyCost - cheapestModel.monthlyCost;
            const savingsPercent = currentModelCost.monthlyCost > 0 ? (savings / currentModelCost.monthlyCost * 100) : 0;
            
            html += `<div style="background: #f8fafc; border-radius: 8px; padding: 15px; margin-bottom: 15px; display: flex; gap: 20px; flex-wrap: wrap;">
                <div>
                    <div style="font-size: 0.85em; color: #6b7280;">Your model</div>
                    <div style="font-weight: 600; color: #1e293b;">${currentModelCost.name}</div>
                    <div style="font-size: 0.9em; color: #2563eb;">${formatCurrency(currentModelCost.monthlyCost)}/mo</div>
                </div>
                <div>
                    <div style="font-size: 0.85em; color: #6b7280;">Rank</div>
                    <div style="font-weight: 600; color: #1e293b;">#${currentRank} of ${modelCosts.length}</div>
                </div>
                ${savings > 0 ? `<div>
                    <div style="font-size: 0.85em; color: #6b7280;">Potential savings</div>
                    <div style="font-weight: 600; color: #059669;">${formatCurrency(savings)}/mo (${savingsPercent.toFixed(0)}%)</div>
                    <div style="font-size: 0.85em; color: #6b7280;">vs ${cheapestModel.name}</div>
                </div>` : `<div>
                    <div style="font-size: 0.85em; color: #6b7280;">Status</div>
                    <div style="font-weight: 600; color: #059669;">✓ Cheapest option!</div>
                </div>`}
            </div>`;
        }
        
        const topModels = modelCosts.slice(0, 10);
        const showCurrentSeparately = currentRank > 10;
        
        html += `
            <table class="comparison-table">
                <thead>
                    <tr>
                        <th>#</th>
                        <th>Model</th>
                        <th>Provider</th>
                        <th>$/Request</th>
                        <th>$/Month</th>
                        <th>vs Current</th>
                        <th>Context</th>
                    </tr>
                </thead>
                <tbody>
        `;
        
        const tableRows = _(topModels)
            .map((m, i) => {
                const rank = i + 1;
                const isCurrentRow = m.isCurrent;
                const rowStyle = isCurrentRow ? 'background: #eff6ff; border-left: 3px solid #2563eb;' : 
                                (rank === 1 ? 'background: #f0fdf4;' : '');
                
                const diffFromCurrent = currentModelCost ? (m.monthlyCost - currentModelCost.monthlyCost) : 0;
                const diffClass = diffFromCurrent < 0 ? 'delta-positive' : (diffFromCurrent > 0 ? 'delta-negative' : '');
                const diffSign = diffFromCurrent > 0 ? '+' : '';
                const diffText = isCurrentRow ? '—' : `${diffSign}${formatCurrency(diffFromCurrent)}`;
                
                return `
                    <tr style="${rowStyle}">
                        <td>${rank}</td>
                        <td>
                            <strong>${m.name}</strong>
                            ${rank === 1 ? ' <span class="tag tag-green">Cheapest</span>' : ''}
                            ${isCurrentRow ? ' <span class="tag tag-blue">Current</span>' : ''}
                        </td>
                        <td>${m.provider}</td>
                        <td>${formatCurrency(m.costPerRequest, 4)}</td>
                        <td>${formatCurrency(m.monthlyCost)}</td>
                        <td class="${diffClass}">${diffText}</td>
                        <td>${(m.contextWindow / 1000).toFixed(0)}K</td>
                    </tr>
                `;
            })
            .value()
            .join('');
        
        html += tableRows;
        
        if (showCurrentSeparately && currentModelCost) {
            html += `
                <tr style="border-top: 2px dashed #e5e7eb;">
                    <td colspan="7" style="text-align: center; color: #6b7280; font-size: 0.85em; padding: 5px;">... ${currentRank - 11} models ...</td>
                </tr>
                <tr style="background: #eff6ff; border-left: 3px solid #2563eb;">
                    <td>${currentRank}</td>
                    <td><strong>${currentModelCost.name}</strong> <span class="tag tag-blue">Current</span></td>
                    <td>${currentModelCost.provider}</td>
                    <td>${formatCurrency(currentModelCost.costPerRequest, 4)}</td>
                    <td>${formatCurrency(currentModelCost.monthlyCost)}</td>
                    <td>—</td>
                    <td>${(currentModelCost.contextWindow / 1000).toFixed(0)}K</td>
                </tr>
            `;
        }
        
        html += '</tbody></table>';
        
        // Mobile cards
        const cardsHtml = _(topModels)
            .map((m, i) => {
                const rank = i + 1;
                const isCurrentRow = m.isCurrent;
                const cardClass = isCurrentRow ? 'current' : (rank === 1 ? 'cheapest' : '');
                
                const diffFromCurrent = currentModelCost ? (m.monthlyCost - currentModelCost.monthlyCost) : 0;
                const diffClass = diffFromCurrent < 0 ? 'delta-positive' : (diffFromCurrent > 0 ? 'delta-negative' : '');
                const diffSign = diffFromCurrent > 0 ? '+' : '';
                const diffText = isCurrentRow ? '—' : `${diffSign}${formatCurrency(diffFromCurrent)}`;
                
                return `
                    <div class="comparison-card ${cardClass}">
                        <div class="comparison-card-header">
                            <div>
                                <div class="comparison-card-title">${m.name}</div>
                                <div style="margin-top: 4px;">
                                    ${rank === 1 ? '<span class="tag tag-green">Cheapest</span>' : ''}
                                    ${isCurrentRow ? '<span class="tag tag-blue">Current</span>' : ''}
                                </div>
                            </div>
                            <div class="comparison-card-rank">#${rank}</div>
                        </div>
                        <div class="comparison-card-grid">
                            <div class="comparison-card-item">
                                <div class="comparison-card-label">Provider</div>
                                <div class="comparison-card-value">${m.provider}</div>
                            </div>
                            <div class="comparison-card-item">
                                <div class="comparison-card-label">Context</div>
                                <div class="comparison-card-value">${(m.contextWindow / 1000).toFixed(0)}K</div>
                            </div>
                            <div class="comparison-card-item">
                                <div class="comparison-card-label">$/Request</div>
                                <div class="comparison-card-value">${formatCurrency(m.costPerRequest, 4)}</div>
                            </div>
                            <div class="comparison-card-item">
                                <div class="comparison-card-label">$/Month</div>
                                <div class="comparison-card-value">${formatCurrency(m.monthlyCost)}</div>
                            </div>
                            <div class="comparison-card-item">
                                <div class="comparison-card-label">vs Current</div>
                                <div class="comparison-card-value ${diffClass}">${diffText}</div>
                            </div>
                        </div>
                    </div>
                `;
            })
            .value()
            .join('');
        
        html += `<div class="comparison-cards">${cardsHtml}</div>`;
        html += `<p style="font-size: 0.8em; color: #6b7280; margin-top: 10px;">Showing top 10 of ${modelCosts.length} models. Costs based on your configuration: ${formValues.inputTokens} input × ${formValues.outputTokens} output tokens, ${monthlyRequests.toLocaleString()} requests/month.</p>`;
        
        $el('model-comparison-table').html(html);
    };
    
    // Scenario management
    const saveScenario = () => {
        if (!window.currentCalc) return;
        
        const scenario = {
            ...window.currentCalc,
            id: Date.now(),
            name: `${window.currentCalc.model} - ${new Date().toLocaleTimeString()}`
        };
        
        savedScenarios.push(scenario);
        renderSavedScenarios();
    };
    
    const renderSavedScenarios = () => {
        if (savedScenarios.length === 0) {
            $el('saved-scenarios').html('<p style="color: #6b7280; font-size: 0.9em;">No scenarios saved yet.</p>');
            return;
        }
        
        const scenariosHtml = _(savedScenarios)
            .map((s, i) => `
                <div class="scenario-card" onclick="loadScenario(${i})">
                    <div style="display: flex; justify-content: space-between;">
                        <h4 style="margin: 0;">${s.model}</h4>
                        <button onclick="event.stopPropagation(); removeScenario(${i})" style="background: none; border: none; color: #dc2626; cursor: pointer;">×</button>
                    </div>
                    <p>$${s.costPerRequest.toFixed(4)}/req · $${s.monthlyCost.toFixed(2)}/mo · ${s.monthlyRequests.toLocaleString()} req/mo</p>
                </div>
            `)
            .value()
            .join('');
        
        $el('saved-scenarios').html(scenariosHtml);
    };
    
    const loadScenario = (index) => {
        const s = savedScenarios[index];
        if (!s) return;
        
        $el('provider-select').val(s.provider);
        updateModels();
        $el('model-select').val(s.modelId);
        $el('input-tokens').val(s.inputTokens);
        $el('output-tokens').val(s.outputTokens);
        $el('iterations').val(s.iterations);
        $el('daily-users').val(s.dailyUsers);
        $el('requests-per-user').val(s.requestsPerUser);
        $el('scale-select').val(s.scale);
        $el('complexity-select').val(s.complexity);
        
        updateModelSpecs();
    };
    
    const removeScenario = (index) => {
        savedScenarios.splice(index, 1);
        renderSavedScenarios();
    };
    
    const clearScenarios = () => {
        savedScenarios = [];
        renderSavedScenarios();
    };
    
    const showDelta = () => {
        if (savedScenarios.length < 2) {
            alert('Save at least 2 scenarios to compare deltas');
            return;
        }
        
        const baseline = savedScenarios[0];
        
        const deltaRows = _(savedScenarios)
            .map((s, i) => {
                const deltaPerReq = s.costPerRequest - baseline.costPerRequest;
                const deltaMonthly = s.monthlyCost - baseline.monthlyCost;
                const deltaPercent = baseline.monthlyCost > 0 ? ((s.monthlyCost - baseline.monthlyCost) / baseline.monthlyCost * 100) : 0;
                
                const deltaClass = deltaMonthly > 0 ? 'delta-negative' : (deltaMonthly < 0 ? 'delta-positive' : '');
                const deltaSign = deltaMonthly > 0 ? '+' : '';
                
                return `
                    <tr ${i === 0 ? 'style="background: #f8fafc;"' : ''}>
                        <td><strong>${s.model}</strong>${i === 0 ? ' (baseline)' : ''}</td>
                        <td>$${s.costPerRequest.toFixed(4)}</td>
                        <td class="${deltaClass}">${i === 0 ? '-' : deltaSign + '$' + deltaPerReq.toFixed(4)}</td>
                        <td>$${s.monthlyCost.toFixed(2)}</td>
                        <td class="${deltaClass}">${i === 0 ? '-' : deltaSign + '$' + deltaMonthly.toFixed(2)}</td>
                        <td class="${deltaClass}">${i === 0 ? '-' : deltaSign + deltaPercent.toFixed(1) + '%'}</td>
                    </tr>
                `;
            })
            .value()
            .join('');
        
        const cheapest = _.minBy(savedScenarios, s => s.monthlyCost);
        const mostExpensive = _.maxBy(savedScenarios, s => s.monthlyCost);
        const savings = mostExpensive.monthlyCost - cheapest.monthlyCost;
        
        $el('delta-comparison-content').html(`
            <p style="color: #6b7280;">Comparing against baseline: <strong>${baseline.model}</strong></p>
            <table class="comparison-table">
                <thead>
                    <tr>
                        <th>Scenario</th>
                        <th>$/Request</th>
                        <th>Δ $/Request</th>
                        <th>$/Month</th>
                        <th>Δ $/Month</th>
                        <th>Δ %</th>
                    </tr>
                </thead>
                <tbody>
                    ${deltaRows}
                </tbody>
            </table>
            <div style="margin-top: 20px; padding: 15px; background: #f0fdf4; border-radius: 8px;">
                <strong style="color: #059669;">Potential Savings:</strong>
                <p style="margin: 5px 0 0 0;">
                    Switching from <strong>${mostExpensive.model}</strong> to <strong>${cheapest.model}</strong> 
                    saves <strong>$${savings.toFixed(2)}/month</strong> 
                    (${((savings / mostExpensive.monthlyCost) * 100).toFixed(1)}% reduction)
                </p>
            </div>
        `);
        
        $el('delta-modal').removeClass('hidden');
    };
    
    const hideDelta = () => {
        $el('delta-modal').addClass('hidden');
    };

    // The backdrop and Escape are the only way out — the modal carries no close button. The
    // target test is what keeps a click inside the card from dismissing it, since that click
    // bubbles up to the backdrop too.
    $('#delta-modal').on('click', (e) => { if (e.target.id === 'delta-modal') hideDelta(); });
    document.addEventListener('keydown', (e) => { if (e.key === 'Escape') hideDelta(); });

    const showComparison = () => {
        generateModelComparison();
        document.getElementById('comparison')?.scrollIntoView({ behavior: 'smooth' });
    };
    
    const exportResults = () => {
        if (!window.currentCalc) return;
        
        const data = {
            calculation: window.currentCalc,
            savedScenarios: savedScenarios,
            exportedAt: new Date().toISOString()
        };
        
        const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `thrifty-tco-${Date.now()}.json`;
        a.click();
    };
    
        // Initialize
        const init = async () => {
            console.log('Initializing Thrifty TCO Calculator...');
            
            models = await fetchModels();
            console.log(`Loaded ${_.size(models)} models from ${_.size(providers)} providers`);
            
            if (_.size(models) === 0) {
                $el('model-info').text('No models loaded - check API connection');
            }
            
            updateProviders();
            renderUseCaseTemplates();
            updateRecommendations();
            generateModelComparison();
        };
        
        // Event bindings
        window.applyUseCase = applyUseCase;
        window.updateModels = updateModels;
        window.updateModelSpecs = updateModelSpecs;
        window.recalculateAll = recalculateAll;
        window.updateRecommendations = updateRecommendations;
        window.showPlatformTab = showPlatformTab;
        window.selectUseCaseTemplate = selectUseCaseTemplate;
        window.saveScenario = saveScenario;
        window.loadScenario = loadScenario;
        window.removeScenario = removeScenario;
        window.clearScenarios = clearScenarios;
        window.showDelta = showDelta;
        window.hideDelta = hideDelta;
        window.showComparison = showComparison;
        window.exportResults = exportResults;
        
        // Run initialization
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', init);
        } else {
            init();
        }
    };
    
    initApp();
})();
