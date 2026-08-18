from fasthtml.common import (Html, Head, Body, Meta, Title, Link, Socials, Script, Nav, Div, Span, P, A, H1, H2,
                             Label, Select, Option, Input, Button, NotStr)
from fastcore.all import Path
from lego.core import asset_css, asset_js, vendor_js, rendered
from .cfg import cfg
from .data import get_use_case_templates, page_data

__all__ = ['page']

here = Path(__file__).parent
GH_SVG = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" aria-hidden="true">'
          '<path d="M8 .25a.75.75 0 0 1 .673.418l1.882 3.815 4.21.612a.75.75 0 0 1 .416 1.279l-3.046 2.97.719 '
          '4.192a.751.751 0 0 1-1.088.791L8 12.347l-3.766 1.98a.75.75 0 0 1-1.088-.79l.72-4.194L.818 6.374a.75.75 '
          '0 0 1 .416-1.28l4.21-.611L7.327.668A.75.75 0 0 1 8 .25Zm0 2.445L6.615 5.5a.75.75 0 0 1-.564.41l-3.097.45 '
          '2.24 2.184a.75.75 0 0 1 .216.664l-.528 3.084 2.769-1.456a.75.75 0 0 1 .698 0l2.77 1.456-.53-3.084a.75.75 '
          '0 0 1 .216-.664l2.24-2.183-3.096-.45a.75.75 0 0 1-.564-.41L8 2.694Z"/></svg>')
rule = Div(style='border-top: 1px solid #e5e7eb; margin: 20px 0;')

def head():
    '''thrifty's own head, not the app's.

    Like hora, this block ships a whole document: the page carries its own stylesheet, laid
    out on plain classes of its own, and Oat's reset and theme tokens would restyle every
    input and card in it. So the app-wide head in `lego/app.py` never reaches here.

    lodash is the one dependency, served from static/vendor behind the immutable mount with
    a content-hashed ?v= — upstream fetched `lodash@latest` from a CDN at runtime.'''
    url = f'https://{cfg.domain}'
    return Head(
        Meta(charset='UTF-8'),
        Meta(name='viewport', content='width=device-width, initial-scale=1'),
        Meta(name='theme-color', content=cfg.theme_color),
        Meta(name='description', content=cfg.tagline),
        Meta(name='robots', content='index, follow'),
        Title(f'{cfg.title} — {cfg.subtitle}'),
        Link(rel='canonical', href=url),
        Link(rel='icon', type='image/svg+xml', href='/static/favicon.svg'),
        *Socials(title=cfg.title, description=cfg.tagline, site_name=cfg.domain,
                 image='/static/favicon.svg', url=url),
        asset_css(here / 'thrifty.css'),
        vendor_js('lodash.min.js'))

def header():
    'Title, the star link, and the in-page nav.'
    return Div(Div(
        Div(H1(cfg.title), P(cfg.subtitle, cls='header-subtitle'), cls='header-left'),
        A(NotStr(GH_SVG), Span('Star on GitHub'), href=f'https://github.com/{cfg.repo}',
          target='_blank', rel='noopener noreferrer', cls='github-star'),
        Nav(A('Calculator', href='#calculator', cls='active'), A('Templates', href='#use-cases'),
            A('Platforms', href='#platforms'), A('Comparison', href='#comparison'), cls='nav'),
        cls='header-content'), cls='header')

def tco_summary():
    def item(id, label, v='$0'): return Div(Div(v, cls='value', id=id), Div(label, cls='label'), cls='tco-item')
    return Div(
        H2('Total Cost of Ownership Summary', style='margin-top: 0;'),
        Div(item('tco-per-request', 'Per Request', '$0.00'), item('tco-monthly', 'Monthly (Est.)'),
            item('tco-platform', 'Platform Costs'), item('tco-total', 'Total Monthly'), cls='tco-grid'),
        cls='tco-summary')

def field(label, ctl, info=None):
    'One labelled control, with an optional line of help under it.'
    return Div(Label(label), ctl, info, cls='form-group')

def calculator_card(use_cases):
    'Everything the estimate is computed from. Every control recalculates in the browser.'
    return Div(
        H2('Cost Calculator'),
        field('Quick Start: Select Use Case',
              Select(Option('Custom Configuration', value=''),
                     *[Option(uc.name, value=k) for k, uc in use_cases.items()],
                     id='use-case-select', onchange='applyUseCase()'),
              Div(id='use-case-info', style='margin-top: 10px;')),
        field('Expected Scale',
              Select(Option('Startup (< 100K req/mo)', value='startup'),
                     Option('Growth (100K - 1M req/mo)', value='growth'),
                     Option('Scale (1M - 10M req/mo)', value='scale'),
                     Option('Enterprise (10M+ req/mo)', value='enterprise'),
                     id='scale-select', onchange='updateRecommendations()')),
        field('Use Case Complexity',
              Select(Option('Low - Simple prompt/response', value='low'),
                     Option('Medium - Multi-step, some context', value='medium'),
                     Option('High - Complex agents, tool use', value='high'),
                     id='complexity-select', onchange='updateRecommendations()')),
        rule,
        field('LLM Provider', Select(id='provider-select', onchange='updateModels()')),
        field('Model', Select(id='model-select', onchange='updateModelSpecs()'), Span(id='model-info', cls='info-text')),
        rule,
        field('Input Tokens per Request',
              Input(type='number', id='input-tokens', value='1000', min='1', oninput='recalculateAll()'),
              Span(id='input-info', cls='info-text')),
        field('Output Tokens per Request',
              Input(type='number', id='output-tokens', value='500', min='1', oninput='recalculateAll()'),
              Span(id='output-info', cls='info-text')),
        rule,
        field('Daily Active Users',
              Input(type='number', id='daily-users', value='100', min='1', oninput='recalculateAll()')),
        field('Requests per User per Day',
              Input(type='number', id='requests-per-user', value='10', min='1', oninput='recalculateAll()')),
        field('Agent Iterations per Request',
              Input(type='number', id='iterations', value='1', min='1', oninput='recalculateAll()'),
              Span('For multi-step agents, enter average iterations', cls='info-text')),
        id='calculator', cls='card')

def results_card():
    def cost(label, id, v='$0', **kw): return Div(Div(label, cls='cost-label'), Div(v, id=id, cls='cost-display', **kw))
    return Div(
        H2('Cost Breakdown'),
        cost('LLM Cost Per Request', 'cost-per-request', '$0.00'),
        Div(Div('LLM Cost Monthly', cls='cost-label'), Div('$0', id='cost-monthly', cls='cost-display monthly')),
        cost('Total Monthly (LLM + Platform)', 'cost-total-monthly', style='color: #7c3aed;'),
        Div(id='breakdown', cls='breakdown'),
        Div(Button('Save Scenario', cls='btn btn-primary', onclick='saveScenario()'),
            Button('Compare Models', cls='btn btn-secondary', onclick='showComparison()'),
            Button('Export', cls='btn btn-success', onclick='exportResults()'), cls='btn-group'),
        cls='card')

def saved_scenarios_card():
    return Div(
        H2('Saved Scenarios'),
        # A child, not a `children=` kwarg: fastcore has no such attribute, so upstream was
        # rendering the placeholder into the div's attributes and never showing it.
        Div(P('No scenarios saved yet. Save configurations to compare.', style='color: #6b7280; font-size: 0.9em;'),
            id='saved-scenarios'),
        Div(Button('Clear All', cls='btn btn-secondary', onclick='clearScenarios()'),
            Button('Show Delta', cls='btn btn-warning', onclick='showDelta()'), cls='btn-group'),
        cls='card', style='margin-top: 25px;')

def section(title, id, blurb, body_id, tabs=None):
    'One of the three scrolled-to panels; the body is filled in by thrifty.js.'
    return Div(H2(title, id=id), P(blurb, style='color: #6b7280; margin-top: -10px;'), tabs,
               Div(id=body_id), cls='card', style='margin-top: 25px;')

def platform_tabs():
    ts = [('Agent Frameworks', 'agent_frameworks'), ('Vector Stores', 'vector_stores'), ('CI/CD', 'cicd'),
          ('Observability', 'observability'), ('Model Registry', 'registries')]
    return Div(*[Button(nm, cls='section-tab active' if i == 0 else 'section-tab',
                        onclick=f"showPlatformTab('{k}')") for i, (nm, k) in enumerate(ts)], cls='section-tabs')

def delta_modal():
    'Backdrop click and Escape close it — thrifty.js binds both, so there is no close button.'
    return Div(Div(H2('Scenario Delta Comparison'), Div(id='delta-comparison-content'),
                   cls='card', style='max-width: 800px; margin: 50px auto;'),
               id='delta-modal', cls='hidden')

def _doc():
    use_cases = get_use_case_templates()
    main = Div(
        tco_summary(),
        Div(calculator_card(use_cases), Div(results_card(), saved_scenarios_card()), cls='grid-2'),
        section('Use Case Templates', 'use-cases',
                'Click a template to auto-configure the calculator with typical values', 'use-case-templates-grid'),
        section('Platform Recommendations', 'platforms', 'Based on your scale and complexity selections',
                'platform-recommendations', platform_tabs()),
        section('Model Cost Comparison', 'comparison', 'Compare costs across models for your use case',
                'model-comparison-table'),
        delta_modal(),
        cls='main-content')
    # The catalogue as data rather than as generated JS, so thrifty.js stays a static file:
    # it reads this tag by id. Both come last, after the elements the script looks up exist.
    data = Script(NotStr(page_data()), type='application/json', id='thrifty-data')
    return Html(head(), Body(header(), main, data, asset_js(here / 'thrifty.js')), lang='en')

def page():
    'The document, serialised once — nothing in it varies by request. `to_xml` adds the doctype.'
    return str(rendered('thrifty', _doc))
