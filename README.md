# Athlete Attendance and Feedback System

An asynchronous Discord application linked with a supabase database designed to automate attendance tracking, collect athlete feedback, and give coaches consistent participation data regardless of roster size.

## The Engineering Problem
Managing attendance and training feedback for a large collegiate team traditionally relies on manual tracking, which is prone to error and data loss. Coaches needed immediate visibility into historical attendance trends to make data-driven decisions for curriculum planning, competition prep, and team projects.

## The Solution
This system integrates directly into the team's official Discord server to provide frictionless, secure attendance logging and analytics, replacing manual workflows with a high-availability cloud architecture.

## Tech Stack & Architecture
* **Language:** Python 3
* **Framework:** `discord.py`
* **Database:** PostgreSQL (Supabase) utilizing `psycopg` connection pooling.
* **Data Visualization:** Matplotlib (configured with headless `Agg` backend for server environments)
* **Infrastructure:** Deployed as a continuous background worker on an AWS EC2 instance.

## Core Features

### 1. High-Availability Database Integration
* **Connection Pooling:** Leverages `psycopg` asynchronous connection pooling to keep the system available for multiple users and handle high-traffic spikes at the end of practice.
* **Optimized Queries:** Wrote asynchronous Python and SQL functions to execute single-pass loops, calculating running attendance percentages while maintaining optimal time complexity.

### 2. Automated Session & Absence Management
* **Smart Practice Windows:** Coaches utilize slash commands to open secure attendance windows mapped to specific academic quarters and training disciplines.
* **Background Auditing:** Utilizes `discord.ext.tasks` for automatic session checks, automatically closing stale windows and recording unexcused absences for the remaining roster with less manual setup during practices..

### 3. Concurrent Athlete Feedback Collection
* **Persistent Discord Controls:** Uses persistent UI views and Discord modals to capture athlete feedback and questions seamlessly..
* **Data Validation:** Implements backend SQL validation checks to prevent duplicate submissions and ensure athletes can only log attendance once per active session.

### 4. Dynamic Analytics & Visualization
* **Automated Reports:** Built automated attendance reports and graphs so coaches can turn stored practice data into clearer information for training and team decisions.
* **In-Memory Graphing:** Generates customized Matplotlib attendance line graphs entirely in-memory using the `Agg` backend, delivering instant visual reports through the Discord API without permanently consuming server storage.