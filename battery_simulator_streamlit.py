import streamlit as st
import pandas as pd
import numpy as np
import time
import random
from datetime import datetime, timedelta
import json
import io

# Configure Streamlit page
st.set_page_config(
    page_title="Battery Cell Simulator",
    page_icon="🔋",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #1e3a8a 0%, #3b82f6 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
    }
    .cell-card {
        background: white;
        padding: 1rem;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        border-left: 4px solid #3b82f6;
        margin-bottom: 1rem;
    }
    .metric-card {
        background: #f8fafc;
        padding: 1rem;
        border-radius: 8px;
        text-align: center;
        border: 1px solid #e2e8f0;
    }
    .status-idle { background-color: #f3f4f6; color: #374151; }
    .status-charging { background-color: #dcfce7; color: #166534; }
    .status-discharging { background-color: #fee2e2; color: #991b1b; }
    .stSelectbox > div > div { background-color: white; }
</style>
""", unsafe_allow_html=True)

# Battery cell types configuration
CELL_TYPES = {
    'lfp': {'name': 'LFP', 'voltage': 3.2, 'min_voltage': 2.8, 'max_voltage': 3.6, 'color': '#10b981'},
    'li-ion': {'name': 'Li-ion', 'voltage': 3.6, 'min_voltage': 3.2, 'max_voltage': 4.0, 'color': '#3b82f6'},
    'nmc': {'name': 'NMC', 'voltage': 3.7, 'min_voltage': 3.0, 'max_voltage': 4.2, 'color': '#8b5cf6'},
    'lto': {'name': 'LTO', 'voltage': 2.4, 'min_voltage': 1.5, 'max_voltage': 2.7, 'color': '#f59e0b'}
}

# Initialize session state
if 'cells' not in st.session_state:
    st.session_state.cells = []
if 'simulation_data' not in st.session_state:
    st.session_state.simulation_data = []
if 'is_running' not in st.session_state:
    st.session_state.is_running = False
if 'current_time' not in st.session_state:
    st.session_state.current_time = 0
if 'start_time' not in st.session_state:
    st.session_state.start_time = None

def create_cell(cell_type):
    """Create a new battery cell with default parameters"""
    config = CELL_TYPES[cell_type]
    cell_id = f"cell_{len(st.session_state.cells) + 1}_{cell_type}"
    
    cell = {
        'id': cell_id,
        'type': cell_type,
        'voltage': config['voltage'] + random.uniform(-0.1, 0.1),
        'current': 0.0,
        'temperature': round(random.uniform(25, 35), 1),
        'capacity': round(random.uniform(90, 100), 1),
        'min_voltage': config['min_voltage'],
        'max_voltage': config['max_voltage'],
        'status': 'idle',
        'task_queue': [],
        'current_task': None,
        'task_start_time': None,
        'color': config['color']
    }
    return cell

def simulate_cell_step(cell):
    """Simulate one step for a cell"""
    if not cell['current_task']:
        return cell
    
    task = cell['current_task']
    
    # Initialize task start time if not set
    if cell['task_start_time'] is None:
        cell['task_start_time'] = st.session_state.current_time
    
    # Calculate task progress
    elapsed_time = st.session_state.current_time - cell['task_start_time']
    
    # Simulate based on task type
    if task['type'] == 'CC_CV':
        # Charging simulation
        if elapsed_time < task['duration'] * 0.7:  # CC phase
            cell['current'] = float(task['current'])
            cell['voltage'] = min(cell['voltage'] + 0.008, cell['max_voltage'])
            cell['temperature'] = min(cell['temperature'] + 0.05, 45)
            cell['capacity'] = min(cell['capacity'] + 0.1, 100)
        else:  # CV phase
            cell['voltage'] = cell['max_voltage']
            cell['current'] = max(cell['current'] - 0.03, 0)
            cell['temperature'] = max(cell['temperature'] - 0.02, 25)
        cell['status'] = 'charging'
        
    elif task['type'] == 'CC_CD':
        # Discharging simulation
        cell['current'] = -float(task['current'])
        cell['voltage'] = max(cell['voltage'] - 0.006, cell['min_voltage'])
        cell['temperature'] = min(cell['temperature'] + 0.03, 40)
        cell['capacity'] = max(cell['capacity'] - 0.08, 0)
        cell['status'] = 'discharging'
        
    elif task['type'] == 'IDLE':
        # Rest simulation
        cell['current'] = 0
        cell['voltage'] += random.uniform(-0.005, 0.005)
        cell['temperature'] = 25 + (cell['temperature'] - 25) * 0.98
        cell['status'] = 'idle'
    
    # Check if task is completed
    if elapsed_time >= task['duration']:
        cell['current_task'] = None
        cell['task_start_time'] = None
        cell['status'] = 'idle'
        cell['current'] = 0
        
        # Remove completed task from queue
        if task in cell['task_queue']:
            cell['task_queue'].remove(task)
        
        # Start next task if available
        if cell['task_queue']:
            cell['current_task'] = cell['task_queue'][0]
    
    return cell

def simulate_step():
    """Simulate one time step for all cells"""
    if not st.session_state.is_running:
        return
    
    st.session_state.current_time += 1
    
    # Update all cells
    for i, cell in enumerate(st.session_state.cells):
        # Start next task if cell is idle and has tasks in queue
        if not cell['current_task'] and cell['task_queue']:
            cell['current_task'] = cell['task_queue'][0]
            cell['task_start_time'] = None
        
        # Simulate cell
        st.session_state.cells[i] = simulate_cell_step(cell)
    
    # Record data point
    data_point = {'time': st.session_state.current_time}
    for cell in st.session_state.cells:
        data_point[f"{cell['id']}_voltage"] = cell['voltage']
        data_point[f"{cell['id']}_current"] = cell['current']
        data_point[f"{cell['id']}_temperature"] = cell['temperature']
        data_point[f"{cell['id']}_capacity"] = cell['capacity']
    
    st.session_state.simulation_data.append(data_point)

def export_data(format_type):
    """Export simulation data in specified format"""
    if not st.session_state.simulation_data:
        st.warning("No simulation data to export!")
        return None
    
    df = pd.DataFrame(st.session_state.simulation_data)
    
    if format_type == 'csv':
        return df.to_csv(index=False).encode('utf-8')
    elif format_type == 'json':
        export_dict = {
            'cells': st.session_state.cells,
            'simulation_data': st.session_state.simulation_data,
            'export_time': datetime.now().isoformat()
        }
        return json.dumps(export_dict, indent=2).encode('utf-8')
    elif format_type == 'excel':
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Simulation Data', index=False)
            
            # Add cells configuration sheet
            cells_df = pd.DataFrame(st.session_state.cells)
            cells_df.to_excel(writer, sheet_name='Cell Configuration', index=False)
            
            # Add summary statistics
            if len(df) > 0:
                summary_data = []
                for cell in st.session_state.cells:
                    cell_data = {
                        'Cell ID': cell['id'],
                        'Type': cell['type'],
                        'Final Voltage': cell['voltage'],
                        'Final Current': cell['current'],
                        'Final Temperature': cell['temperature'],
                        'Final Capacity': cell['capacity'],
                        'Status': cell['status']
                    }
                    summary_data.append(cell_data)
                
                summary_df = pd.DataFrame(summary_data)
                summary_df.to_excel(writer, sheet_name='Summary', index=False)
        
        return buffer.getvalue()

# Main App Header
st.markdown("""
<div class="main-header">
    <h1>🔋 Advanced Battery Cell Simulation System</h1>
    <p>Professional battery testing and analysis platform</p>
</div>
""", unsafe_allow_html=True)

# Sidebar Controls
with st.sidebar:
    st.header("⚙️ Simulation Controls")
    
    # Time display
    minutes = st.session_state.current_time // 60
    seconds = st.session_state.current_time % 60
    st.metric("Simulation Time", f"{minutes:02d}:{seconds:02d}")
    
    # Control buttons
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("▶️ Start" if not st.session_state.is_running else "⏸️ Pause", 
                    type="primary", use_container_width=True):
            st.session_state.is_running = not st.session_state.is_running
            if st.session_state.is_running and st.session_state.start_time is None:
                st.session_state.start_time = time.time()
    
    with col2:
        if st.button("⏹️ Stop", use_container_width=True):
            st.session_state.is_running = False
            st.session_state.current_time = 0
            st.session_state.simulation_data = []
            st.session_state.start_time = None
            # Reset all cells
            for cell in st.session_state.cells:
                cell['status'] = 'idle'
                cell['current_task'] = None
                cell['task_start_time'] = None
                cell['current'] = 0
    
    st.divider()
    
    # Add Cell Section
    st.header("➕ Add Cells")
    
    selected_cell_type = st.selectbox(
        "Select Cell Type",
        options=list(CELL_TYPES.keys()),
        format_func=lambda x: f"{CELL_TYPES[x]['name']} ({x.upper()})"
    )
    
    if st.button("Add Cell", use_container_width=True):
        new_cell = create_cell(selected_cell_type)
        st.session_state.cells.append(new_cell)
        st.success(f"Added {new_cell['id']}")
    
    st.divider()
    
    # Export Section
    st.header("📊 Export Data")
    
    if st.session_state.simulation_data:
        st.write(f"Data points: {len(st.session_state.simulation_data)}")
        
        export_format = st.selectbox("Export Format", ["CSV", "JSON", "Excel"])
        
        if st.button("📥 Export Data", use_container_width=True):
            format_map = {"CSV": "csv", "JSON": "json", "Excel": "excel"}
            data = export_data(format_map[export_format])
            
            if data:
                filename = f"battery_simulation_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                if export_format == "CSV":
                    st.download_button(
                        "Download CSV", data, f"{filename}.csv", "text/csv"
                    )
                elif export_format == "JSON":
                    st.download_button(
                        "Download JSON", data, f"{filename}.json", "application/json"
                    )
                elif export_format == "Excel":
                    st.download_button(
                        "Download Excel", data, f"{filename}.xlsx", 
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
    else:
        st.info("No data to export")

# Main content area
tab1, tab2, tab3, tab4 = st.tabs(["🔋 Cells", "📈 Real-time Charts", "📊 Analysis", "⚙️ Task Management"])

with tab1:
    st.header("Battery Cells Overview")
    
    if not st.session_state.cells:
        st.info("No cells added yet. Use the sidebar to add battery cells.")
    else:
        # Display cells in a grid
        cols_per_row = 3
        for i in range(0, len(st.session_state.cells), cols_per_row):
            cols = st.columns(cols_per_row)
            
            for j, col in enumerate(cols):
                if i + j < len(st.session_state.cells):
                    cell = st.session_state.cells[i + j]
                    
                    with col:
                        # Cell card
                        st.markdown(f"""
                        <div class="cell-card">
                            <h4 style="color: {cell['color']}">🔋 {cell['id']}</h4>
                            <p><strong>Type:</strong> {CELL_TYPES[cell['type']]['name']}</p>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        # Metrics
                        metric_col1, metric_col2 = st.columns(2)
                        with metric_col1:
                            st.metric("Voltage", f"{cell['voltage']:.2f}V")
                            st.metric("Temperature", f"{cell['temperature']:.1f}°C")
                        with metric_col2:
                            st.metric("Current", f"{cell['current']:.2f}A")
                            st.metric("Capacity", f"{cell['capacity']:.1f}%")
                        
                        # Status
                        status_class = f"status-{cell['status']}"
                        st.markdown(f"""
                        <div class="{status_class}" style="padding: 5px; border-radius: 5px; text-align: center; margin: 10px 0;">
                            <strong>Status:</strong> {cell['status'].upper()}
                        </div>
                        """, unsafe_allow_html=True)
                        
                        # Task queue info
                        if cell['task_queue']:
                            st.write(f"**Tasks in queue:** {len(cell['task_queue'])}")
                            for idx, task in enumerate(cell['task_queue'][:3]):  # Show first 3 tasks
                                active = "🔄" if idx == 0 and cell['current_task'] else "⏸️"
                                st.write(f"{active} {task['type']} ({task['duration']}s)")
                        
                        # Control buttons
                        if st.button(f"🎲 Randomize", key=f"rand_{cell['id']}"):
                            config = CELL_TYPES[cell['type']]
                            cell['voltage'] = config['voltage'] + random.uniform(-0.2, 0.2)
                            cell['temperature'] = round(random.uniform(25, 35), 1)
                            cell['capacity'] = round(random.uniform(80, 100), 1)
                            st.success(f"Randomized {cell['id']}")
                        
                        if st.button(f"🗑️ Remove", key=f"remove_{cell['id']}"):
                            st.session_state.cells = [c for c in st.session_state.cells if c['id'] != cell['id']]
                            st.success(f"Removed {cell['id']}")
                            st.rerun()

with tab2:
    st.header("Real-time Monitoring")
    
    if st.session_state.simulation_data and st.session_state.cells:
        # Create subplots
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=('Voltage', 'Current', 'Temperature', 'Capacity'),
            specs=[[{"secondary_y": False}, {"secondary_y": False}],
                   [{"secondary_y": False}, {"secondary_y": False}]]
        )
        
        # Get recent data (last 100 points)
        recent_data = st.session_state.simulation_data[-100:]
        df = pd.DataFrame(recent_data)
        
        if not df.empty:
            for cell in st.session_state.cells:
                cell_id = cell['id']
                color = cell['color']
                
                # Voltage
                if f"{cell_id}_voltage" in df.columns:
                    fig.add_trace(
                        go.Scatter(x=df['time'], y=df[f"{cell_id}_voltage"], 
                                 name=f"{cell_id}", line=dict(color=color)),
                        row=1, col=1
                    )
                
                # Current
                if f"{cell_id}_current" in df.columns:
                    fig.add_trace(
                        go.Scatter(x=df['time'], y=df[f"{cell_id}_current"], 
                                 name=f"{cell_id}", line=dict(color=color), showlegend=False),
                        row=1, col=2
                    )
                
                # Temperature
                if f"{cell_id}_temperature" in df.columns:
                    fig.add_trace(
                        go.Scatter(x=df['time'], y=df[f"{cell_id}_temperature"], 
                                 name=f"{cell_id}", line=dict(color=color), showlegend=False),
                        row=2, col=1
                    )
                
                # Capacity
                if f"{cell_id}_capacity" in df.columns:
                    fig.add_trace(
                        go.Scatter(x=df['time'], y=df[f"{cell_id}_capacity"], 
                                 name=f"{cell_id}", line=dict(color=color), showlegend=False),
                        row=2, col=2
                    )
            
            # Update layout
            fig.update_layout(height=600, title_text="Real-time Battery Parameters")
            fig.update_xaxes(title_text="Time (s)")
            fig.update_yaxes(title_text="Voltage (V)", row=1, col=1)
            fig.update_yaxes(title_text="Current (A)", row=1, col=2)
            fig.update_yaxes(title_text="Temperature (°C)", row=2, col=1)
            fig.update_yaxes(title_text="Capacity (%)", row=2, col=2)
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Auto-refresh when simulation is running
            if st.session_state.is_running:
                simulate_step()
                time.sleep(0.1)  # Small delay to prevent overwhelming
                st.rerun()
    else:
        st.info("Start simulation to see real-time charts")

with tab3:
    st.header("Data Analysis")
    
    if st.session_state.cells:
        # Current cell comparison
        st.subheader("Current Cell Status Comparison")
        
        comparison_data = []
        for cell in st.session_state.cells:
            comparison_data.append({
                'Cell ID': cell['id'],
                'Type': CELL_TYPES[cell['type']]['name'],
                'Voltage (V)': cell['voltage'],
                'Current (A)': cell['current'],
                'Temperature (°C)': cell['temperature'],
                'Capacity (%)': cell['capacity'],
                'Status': cell['status']
            })
        
        comparison_df = pd.DataFrame(comparison_data)
        st.dataframe(comparison_df, use_container_width=True)
        
        # Bar chart comparison
        fig_bar = go.Figure()
        
        metrics = ['Voltage (V)', 'Current (A)', 'Temperature (°C)', 'Capacity (%)']
        selected_metric = st.selectbox("Select metric for comparison", metrics)
        
        colors = [st.session_state.cells[i]['color'] for i in range(len(st.session_state.cells))]
        
        fig_bar.add_trace(go.Bar(
            x=comparison_df['Cell ID'],
            y=comparison_df[selected_metric],
            marker_color=colors,
            name=selected_metric
        ))
        
        fig_bar.update_layout(
            title=f"Cell {selected_metric} Comparison",
            xaxis_title="Cell ID",
            yaxis_title=selected_metric
        )
        
        st.plotly_chart(fig_bar, use_container_width=True)
        
        # Statistics
        if st.session_state.simulation_data:
            st.subheader("Simulation Statistics")
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Total Runtime", f"{st.session_state.current_time}s")
            with col2:
                st.metric("Data Points", len(st.session_state.simulation_data))
            with col3:
                st.metric("Active Cells", len(st.session_state.cells))
            with col4:
                active_tasks = sum(1 for cell in st.session_state.cells if cell['current_task'])
                st.metric("Active Tasks", active_tasks)

with tab4:
    st.header("Task Management")
    
    if not st.session_state.cells:
        st.info("Add cells first to manage tasks")
    else:
        # Task creation form
        st.subheader("Add New Task")
        
        col1, col2 = st.columns(2)
        
        with col1:
            selected_cell = st.selectbox(
                "Select Cell",
                options=[cell['id'] for cell in st.session_state.cells]
            )
            
            task_type = st.selectbox(
                "Task Type",
                options=['CC_CV', 'CC_CD', 'IDLE'],
                help="CC_CV: Charge, CC_CD: Discharge, IDLE: Rest"
            )
        
        with col2:
            if task_type != 'IDLE':
                current_value = st.number_input("Current (A)", min_value=0.1, max_value=10.0, value=1.0, step=0.1)
            
            if task_type == 'CC_CV':
                voltage_value = st.number_input("CV Voltage (V)", min_value=3.0, max_value=4.5, value=4.0, step=0.1)
            
            duration = st.number_input("Duration (seconds)", min_value=10, max_value=3600, value=300, step=10)
        
        if st.button("Add Task", type="primary"):
            task = {
                'type': task_type,
                'duration': duration
            }
            
            if task_type != 'IDLE':
                task['current'] = current_value
            
            if task_type == 'CC_CV':
                task['voltage'] = voltage_value
            
            # Find the selected cell and add task
            for cell in st.session_state.cells:
                if cell['id'] == selected_cell:
                    cell['task_queue'].append(task)
                    break
            
            st.success(f"Added {task_type} task to {selected_cell}")
        
        st.divider()
        
        # Display current task queues
        st.subheader("Current Task Queues")
        
        for cell in st.session_state.cells:
            if cell['task_queue']:
                st.write(f"**{cell['id']}** ({len(cell['task_queue'])} tasks)")
                
                task_data = []
                for i, task in enumerate(cell['task_queue']):
                    status = "🔄 Running" if i == 0 and cell['current_task'] else "⏸️ Queued"
                    task_info = {
                        'Position': i + 1,
                        'Type': task['type'],
                        'Duration (s)': task['duration'],
                        'Status': status
                    }
                    
                    if 'current' in task:
                        task_info['Current (A)'] = task['current']
                    if 'voltage' in task:
                        task_info['Voltage (V)'] = task['voltage']
                    
                    task_data.append(task_info)
                
                task_df = pd.DataFrame(task_data)
                st.dataframe(task_df, use_container_width=True)
                
                # Clear tasks button
                if st.button(f"Clear Tasks for {cell['id']}", key=f"clear_{cell['id']}"):
                    cell['task_queue'] = []
                    cell['current_task'] = None
                    cell['task_start_time'] = None
                    cell['status'] = 'idle'
                    st.success(f"Cleared tasks for {cell['id']}")
                    st.rerun()
                
                st.divider()

# Auto-refresh for real-time simulation
if st.session_state.is_running:
    time.sleep(1)
    st.rerun()

# Footer
st.markdown("---")
st.markdown("🔋 **Battery Cell Simulator** - Professional battery testing and analysis platform")
