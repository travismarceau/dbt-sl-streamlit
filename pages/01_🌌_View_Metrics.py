# third party
import plotly.express as px
import streamlit as st

st.set_page_config(
    page_title='dbt Semantic Layer - View Metrics',
    page_icon='🌌',
    layout='wide',
)

if 'conn' not in st.session_state or st.session_state.conn is None:
    st.warning('Go to home page and enter your JDBC URL')
    st.stop()
 

# first party
from client import submit_query
from helpers import get_shared_elements
from query import SemanticLayerQuery


def get_time_length(interval):
    time_lengths = {
        'day': 1,
        'week': 7,
        'month': 30,
        'quarter': 90,
        'year': 365
    }
    return time_lengths.get(interval, 0)


def sort_by_time_length(time_intervals):
    return sorted(time_intervals, key=lambda x: get_time_length(x))


def add_where_state():
    st.session_state.where_items += 1
    

def subtract_where_state():
    st.session_state.where_items -= 1
    i = st.session_state.where_items
    for component in ['column', 'operator', 'condition', 'add', 'subtract']:
        where_component = f'where_{component}_{i}'
        if where_component in st.session_state:
            del st.session_state[where_component]
            
            
def add_order_state():
    st.session_state.order_items += 1
    

def subtract_order_state():
    st.session_state.order_items -= 1
    i = st.session_state.order_items
    for component in ['column', 'direction', 'add', 'subtract']:
        order_component = f'order_{component}_{i}'
        if order_component in st.session_state:
            del st.session_state[order_component]


# Initialize number of items in where clause
if 'where_items' not in st.session_state:
    st.session_state.where_items = 0

# Initialize number of items in order by clause
if 'order_items' not in st.session_state:
    st.session_state.order_items = 0


st.write('# View Your Metrics')

col1, col2 = st.columns(2)

# Retrieve metrics from dictionary
col1.multiselect(
    label='Select Metric(s)',
    options=sorted(st.session_state.metric_dict.keys()),
    default=None,
    key='selected_metrics',
    placeholder='Select a Metric'
)

# Retrieve unique dimensions based on overlap of metrics selected
all_dimensions = [
    v['dimensions'] for k, v in st.session_state.metric_dict.items()
    if k in st.session_state.selected_metrics
]
unique_dimensions = get_shared_elements(all_dimensions)
col2.multiselect(
    label='Select Dimension(s)',
    options=sorted(unique_dimensions),
    default=None,
    key='selected_dimensions',
    placeholder='Select a dimension'
)

# Only add grain if a time dimension has been selected
if len(unique_dimensions) > 0:
    dimension_types = set([
        st.session_state.dimension_dict[dim]['type'].lower()
        for dim in st.session_state.selected_dimensions
    ])
    if 'time' in dimension_types:
        col1, col2 = st.columns(2)
        grains = [
            st.session_state.metric_dict[metric]['queryable_granularities']
            for metric in st.session_state.selected_metrics
        ]
        col2.selectbox(
            label='Select Grain',
            options=sort_by_time_length(
                [g.strip().lower() for g in get_shared_elements(grains)]
            ),
            key='selected_grain',
        )

# Add sections for filtering and ordering
with st.expander('Filtering:'):
    if st.session_state.where_items == 0:
        st.button('Add Filters', on_click=add_where_state, key='static_filter_add')
    else:
        for i in range(st.session_state.where_items):
            col1, col2, col3, col4, col5 = st.columns([3, 1, 3, 1, 1])
            with col1:
                st.selectbox(
                    label='Select Column',
                    options=sorted(unique_dimensions),
                    key=f'where_column_{i}'
                )
            
            with col2:
                st.selectbox(
                    label='Operator',
                    options=[
                        '=', '>', '<', '>=', '<=', '<>', 'BETWEEN', 'LIKE', 'ILIKE', 'IN'
                    ],
                    key=f'where_operator_{i}',
                )
            
            with col3:
                st.text_input(
                    label='Condition',
                    value='',
                    key=f'where_condition_{i}'
                )
            
            with col4:
                st.button('Add', on_click=add_where_state, key=f'where_add_{i}')
            
            with col5:
                st.button(
                    'Remove',
                    on_click=subtract_where_state,
                    key=f'where_subtract_{i}',
                )

valid_orders = (
    st.session_state.selected_metrics + st.session_state.selected_dimensions
)
with st.expander('Ordering:'):
    if st.session_state.order_items == 0:
        st.button('Add Ordering', on_click=add_order_state, key='static_order_add')
    else:    
        for i in range(st.session_state.order_items):
            col1, col2, col3, col4 = st.columns([4, 2, 1, 1])
            with col1:
                st.selectbox(
                    label='Select Column',
                    options=sorted(valid_orders),
                    key=f'order_column_{i}'
                )
            
            with col2:
                st.selectbox(
                    label='Operator',
                    options=['ASC', 'DESC'],
                    key=f'order_direction_{i}',
                )
            
            with col3:
                st.button('Add', on_click=add_order_state, key=f'order_add_{i}')
            
            with col4:
                st.button(
                    'Remove', on_click=subtract_order_state, key=f'order_subtract_{i}'
                )
    

col1, col2 = st.columns(2)
col1.number_input(
    label='Limit Rows',
    min_value=0,
    value=0,
    key='selected_limit',
    help='Limit the amount of rows returned by the query with a limit clause',
)
col1.caption('If set to 0, no limit will be applied')
col2.selectbox(
    label='Explain Query',
    options=[False, True],
    key='selected_explain',
    help='Return the query from metricflow',
)
col2.caption('If set to true, only the generated query will be returned.')

slq = SemanticLayerQuery(st.session_state)
query = slq.query
st.code(query)

if st.button('Submit Query'):
    if len(st.session_state.selected_metrics) == 0:
        st.warning('You must select at least one metric!')
        st.stop()
    
    with st.spinner('Submitting Query...'):
        df = submit_query(st.session_state.conn, query, True)
        df.columns = [col.lower() for col in df.columns]
    
    if st.session_state.selected_explain:
        st.code(df.iloc[0]['sql'])
    else:
        with st.expander('View Raw Data:'):
            st.write(df)

        with st.expander('View Chart:', expanded=True):
            has_time_dimension = len(slq._time_dimensions) > 0
            if has_time_dimension:
                df.set_index(slq._time_dimensions[0], inplace=True)
            else:
                df['combined'] = df.apply(
                    lambda row: '|'.join(str(row[col]) for col in slq._group_by), axis=1
                )
                df.set_index('combined', inplace=True)
            chart_type = 'line_chart' if has_time_dimension else 'bar_chart'
            getattr(st, chart_type)(df, y=slq.metrics)
