import logging
import asyncio
from fastapi_mail import FastMail, MessageSchema
from mail_config import conf
from jinja2 import Template
from typing import Dict, List
import os
from database import get_db_connection, execute_query  # Fixed import
from datetime import datetime
import pytz

EMAIL_SENDER = conf.MAIL_FROM

def send_plain_mail(subject: str, message: str, from_: str, to: List[str]):
    """Send plain text email"""
    try:
        # Filter valid emails
        valid_emails = [email for email in to if email and not email.startswith("noemail")]
        
        if not valid_emails:
            logging.info("All emails were skipped - no valid recipients.")
            return True

        # Create email message
        email = MessageSchema(
            subject=subject,
            recipients=valid_emails,  # This should be a list, not a string
            body=message,
            subtype="plain"
        )

        # Send email using FastMail
        fm = FastMail(conf)
        
        # Use asyncio to run the async send_message method
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(fm.send_message(email))
        loop.close()
        
        logging.info(f"Email sent successfully to: {', '.join(valid_emails)}")
        return True
        
    except Exception as e:
        logging.exception(f"Error in send_plain_mail: {repr(e)}")
        return False


def send_html_mail(subject: str, html_content: str, from_: str, to: List[str]):
    """Send HTML formatted email"""
    try:
        # Filter valid emails
        valid_emails = [email for email in to if email and not email.startswith("noemail")]
        
        if not valid_emails:
            logging.info("All emails were skipped - no valid recipients.")
            return True

        # Create email message with HTML subtype
        email = MessageSchema(
            subject=subject,
            recipients=valid_emails,
            body=html_content,
            subtype="html"  # Set subtype to HTML
        )

        # Send email using FastMail
        fm = FastMail(conf)
        
        # Use asyncio to run the async send_message method
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(fm.send_message(email))
        loop.close()
        
        logging.info(f"HTML email sent successfully to: {', '.join(valid_emails)}")
        return True
        
    except Exception as e:
        logging.exception(f"Error in send_html_mail: {repr(e)}")
        return False


def send_passenger_complain_email(complain_details: Dict):
    """Send complaint email to war room users"""
    war_room_user_in_depot = []
    s2_admin_users = []
    railway_admin_users = []
    assigned_users_list = []
    
    all_users_to_mail = []
    
    s2_admin_users = []
    railway_admin_users = []
    assigned_users_list = []
    
    all_users_to_mail = []
    
    train_depo = complain_details.get('train_depot', '')
    train_no = str(complain_details.get('train_no', '')).strip()
    complaint_date = complain_details.get('created_at', '') 
    journey_start_date = complain_details.get('date_of_journey', '')

    ist = pytz.timezone('Asia/Kolkata')
    complaint_created_at = datetime.now(ist).strftime("%d %b %Y, %H:%M")

    
    try:
        # Query to get war room users
        query = """
            SELECT u.* 
            FROM user_onboarding_user u 
            JOIN user_onboarding_roles ut ON u.user_type_id = ut.id 
            WHERE ut.name = 'war room user'
        """
        
        conn = get_db_connection()
        war_room_users = execute_query(conn, query)
        conn.close()

        if war_room_users:
            for user in war_room_users:
                # Check if user's depot matches train depot
                user_depo = user.get('depo', '')
                if user_depo and train_depo and train_depo in user_depo:
                    war_room_user_in_depot.append(user)
        else:
            logging.info(f"No war room users found for depot {train_depo} in complaint {complain_details['complain_id']}")
            
        s2_admin_query = """
            SELECT u.* 
            FROM user_onboarding_user u 
            JOIN user_onboarding_roles ut ON u.user_type_id = ut.id 
            WHERE ut.name = 's2 admin'
        """
        conn = get_db_connection()
        s2_admin_users = execute_query(conn, s2_admin_query)
        
        railway_admin_query = """
            SELECT u.* 
            FROM user_onboarding_user u 
            JOIN user_onboarding_roles ut ON u.user_type_id = ut.id 
            WHERE ut.name = 'railway admin'
        """
        railway_admin_users = execute_query(conn, railway_admin_query)
        
        # Updated query to get train access users with better filtering
        assigned_users_query = """
            SELECT u.email, u.id, u.full_name, ta.train_details
            FROM user_onboarding_user u
            JOIN trains_trainaccess ta ON ta.user_id = u.id
            WHERE ta.train_details IS NOT NULL 
            AND ta.train_details != '{}'
            AND ta.train_details != 'null'
        """
        conn = get_db_connection()
        assigned_users_raw = execute_query(conn, assigned_users_query)
        conn.close()
        
        # Get train number and complaint date for filtering
        train_no = str(complain_details.get('train_number', '')).strip()
        
        # Handle created_at whether it's a string or datetime object
        created_at_raw = complain_details.get('created_at', '')
        try:
            if isinstance(created_at_raw, datetime):
                complaint_date = created_at_raw.date()
            elif isinstance(created_at_raw, str):
                if len(created_at_raw) >= 10:
                    complaint_date = datetime.strptime(created_at_raw, "%Y-%m-%d").date()
                else:
                    complaint_date = None
            else:
                complaint_date = None
        except (ValueError, TypeError):
            complaint_date = None
            

        if complaint_date and train_no:
            for user in assigned_users_raw:
                try:
                    train_details_str = user.get('train_details', '{}')
                    
                    # Handle case where train_details might be a string or already parsed
                    if isinstance(train_details_str, str):
                        train_details = json.loads(train_details_str)
                    else:
                        train_details = train_details_str
                    
                    # Check if the train number exists in train_details
                    if train_no in train_details:
                        for access in train_details[train_no]:
                            try:
                                origin_date = datetime.strptime(access.get('origin_date', ''), "%Y-%m-%d").date()
                                end_date_str = access.get('end_date', '')
                                
                                # Check if complaint date falls within the valid range
                                if end_date_str == 'ongoing':
                                    is_valid = complaint_date >= origin_date
                                else:
                                    end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
                                    is_valid = origin_date <= complaint_date <= end_date
                                
                                if is_valid:
                                    assigned_users_list.append(user)
                                    break  # Only need one match per user
                                    
                            except (ValueError, TypeError) as date_error:
                                logging.warning(f"Date parsing error for user {user.get('id')}: {date_error}")
                                continue
                                
                except (json.JSONDecodeError, TypeError) as json_error:
                    logging.warning(f"JSON parsing error for user {user.get('id')}: {json_error}")
                    continue

        # all_users_to_mail = [{"email": "writetohm19@gmail.com"}]
        all_users_to_mail = war_room_user_in_depot + s2_admin_users + railway_admin_users + assigned_users_list
     
    except Exception as e:
        logging.error(f"Error fetching users: {e}")
        logging.error(f"Error fetching users: {e}")

    try:
        # Prepare email content
        subject = f"Complaint received for train number: {complain_details['train_no']}"
        pnr_value = complain_details.get('pnr', 'PNR not provided by passenger')

        
        context = {
            "user_phone_number": complain_details.get('user_phone_number', ''),
            "passenger_name": complain_details.get('passenger_name', ''),
            "train_no": complain_details.get('train_no', ''),
            "train_name": complain_details.get('train_name', ''),
            "pnr": pnr_value,
            "berth": complain_details.get('berth', ''),
            "coach": complain_details.get('coach', ''),
            "complain_id": complain_details.get('complain_id', ''),
            "created_at": complaint_created_at,
            "description": complain_details.get('description', ''),
            "train_depo": complain_details.get('train_depo', ''),
            "complaint_date": complaint_date,
            "start_date_of_journey": journey_start_date,
            'site_name': 'RailSathi',
        }
      
        
        
            # Fallback to inline template if file doesn't exist
        # Define the template content directly
        template_content = """
                <!DOCTYPE html>
                <html lang="en">
                <head>
                    <meta charset="UTF-8">
                    <meta name="viewport" content="width=device-width, initial-scale=1.0">
                    <title>Rail Sathi Complaint Notification</title>
                    <style>
                        /* Import Google Fonts */
                        @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap');
                        
                        /* CSS Variables */
                        :root {
                             --primary-color: #0056D6;
                             --primary-light: #EBF3FF;
                             --primary-dark: #003CA8;
                             --danger-color: #DC2626;
                             --danger-light: #FEF2F2;
                             --success-color: #16A34A;
                             --dark-text: #1E293B;
                             --medium-text: #64748B;
                             --light-text: #94A3B8;
                             --border-color: #E2E8F0;
                             --shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
                             --box-radius: 8px;
                             --accent-color: #FF6B35;
                             --bg-light: #F8FAFC;
                             --info-blue: #0EA5E9;
                             --info-light: #F0F9FF;
                             --warning-color: #F59E0B;
                             --warning-light: #FEF3C7;
                             --row-spacing: 8px;
                        }
                        
                        body {
                            font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
                            line-height: 1.5;
                            color: var(--dark-text);
                            background-color: #f5f8fb;
                            margin: 0;
                            padding: 0;
                        }
                        * {
                            box-sizing: border-box;
                        }
                        
                        .container {
                            max-width: 600px;
                            margin: 0px auto 0;
                            background-color: white;
                            border-radius: 16px;
                            overflow: hidden;
                            box-shadow: 0 8px 30px rgba(0, 0, 0, 0.12);
                            border: 1px solid rgba(0, 0, 0, 0.04);
                        }
                        
                        .header {
                            display: none !important;
                            height: 0 !important;
                            margin: 0 !important;
                            padding: 0 !important;
                            overflow: hidden !important;
                        }
                        
                        .header p {
                            margin: 8px 0 0;
                            opacity: 0.9;
                            font-weight: 300;
                            font-size: 16px;
                            position: relative;
                            z-index: 2;
                        }
                        
                        .header::before {
                            content: '';
                            position: absolute;
                            top: -50px;
                            right: -50px;
                            width: 200px;
                            height: 200px;
                            border-radius: 50%;
                            background: rgba(255,255,255,0.1);
                            z-index: 1;
                        }
                        
                        .header::after {
                            content: '';
                            position: absolute;
                            bottom: -80px;
                            left: -80px;
                            width: 250px;
                            height: 250px;
                            border-radius: 50%;
                            background: rgba(255,255,255,0.05);
                            z-index: 1;
                        }
                        
                        .content {
                            padding: 0px 32px 16px !important;
                        }
                        
                        .greeting {
                            font-size: 16px;
                            margin-top: 0;
                            margin-bottom: 18px;
                            color: var(--medium-text);
                            font-weight: 500;
                        }
                        
                        .alert-tag {
                            display: inline-block;
                            background-color: #fef2f2;
                            color: #b91c1c;
                            border: 1px solid #fecaca;
                            border-radius: 4px;
                            font-size: 14px;
                            font-weight: 600;
                            padding: 4px 12px;
                            margin-bottom: 16px;
                        }
                        
                        .complaint-summary {
                            background: linear-gradient(to bottom right, rgba(255, 255, 255, 0.9), rgba(255, 255, 255, 0.8));
                            border-radius: var(--box-radius);
                            padding: 24px 28px;
                            margin-bottom: 32px;
                            border-left: 4px solid var(--accent-color);
                            position: relative;
                            text-align: center;
                            backdrop-filter: blur(10px);
                            box-shadow: 0 4px 16px rgba(0, 0, 0, 0.05);
                        }
                        
                        .complaint-id-badge {
                            background: var(--accent-color);
                            color: white;
                            font-weight: 600;
                            padding: 6px 14px;
                            border-radius: 50px;
                            font-size: 14px;
                            display: inline-block;
                            box-shadow: 0 2px 8px rgba(255, 107, 53, 0.3);
                            margin-bottom: 8px;
                            letter-spacing: 0.5px;
                        }
                        
                        .complaint-summary h2 {
                            margin: 0 0 12px 0;
                            font-size: 22px;
                            font-weight: 600;
                            color: var(--dark-text);
                        }
                        
                        .timestamp {
                            color: var(--medium-text);
                            font-size: 14px;
                            margin: 0;
                            font-weight: 500;
                        }
                        
                        .card {
                            background-color: white;
                            border-radius: 10px;
                            box-shadow: 0 4px 16px rgba(0, 0, 0, 0.04), 0 2px 6px rgba(0, 0, 0, 0.02);
                            margin-bottom: 28px;
                            overflow: hidden;
                            border: 1px solid rgba(0, 0, 0, 0.05);
                            transition: transform 0.3s ease, box-shadow 0.3s ease;
                        }
                        
                        .card:hover {
                            transform: translateY(-2px);
                            box-shadow: 0 8px 20px rgba(0, 0, 0, 0.06);
                        }
                        
                        .card-header {
                            display: flex;
                            align-items: center;
                            gap: 12px;
                            padding: 16px 20px;
                            border-bottom: 1px solid rgba(0, 0, 0, 0.05);
                            background: linear-gradient(to right, var(--primary-light), #f0f7ff);
                        }
                        
                        .card-icon {
                            font-size: 22px;
                            width: 42px;
                            height: 42px;
                            border-radius: 50%;
                            background: var(--primary-color);
                            color: white;
                            display: flex;
                            align-items: center;
                            justify-content: center;
                            box-shadow: 0 4px 10px rgba(0, 86, 214, 0.3);
                        }
                        
                        .card-title {
                            font-size: 18px;
                            font-weight: 600;
                            margin: 0;
                            color: var(--primary-dark);
                            letter-spacing: -0.2px;
                        }
                        
                        .info-grid {
                            display: grid;
                            grid-template-columns: 1fr 1fr;
                            gap: 20px;
                        }
                        
                        .info-label {
                            text-transform: uppercase;
                            font-size: 13px;
                            font-weight: 600;
                            color: var(--primary-dark);
                            letter-spacing: 0.5px;
                            display: block;
                        }
                        
                        .info-value {
                            font-size: 15px;
                            color: var(--dark-text);
                            font-weight: 500;
                            letter-spacing: -0.2px;
                        }
                        
                        .complaint-description {
                            padding: 20px;
                        }
                        
                        .description-box {
                            background-color: #F9FAFB;
                            border-radius: var(--box-radius);
                            padding: 20px 24px;
                            font-size: 15px;
                            line-height: 1.6;
                            color: var(--dark-text);
                            border-left: 3px solid var(--accent-color);
                            white-space: pre-wrap;
                            box-shadow: 0 2px 6px rgba(0, 0, 0, 0.03);
                            position: relative;
                        }
                        
                        .button-container {
                            text-align: center;
                            margin-top: 36px;
                            margin-bottom: 24px;
                        }
                        
                        .action-button {
                            background: linear-gradient(to right, var(--primary-color), var(--primary-dark));
                            color: white;
                            font-weight: 600;
                            text-decoration: none;
                            padding: 14px 28px;
                            border-radius: 30px;
                            font-size: 16px;
                            display: inline-block;
                            box-shadow: 0 4px 12px rgba(0, 86, 214, 0.25);
                            transition: transform 0.3s ease, box-shadow 0.3s ease;
                            letter-spacing: 0.3px;
                        }
                        
                        .action-button:hover {
                            transform: translateY(-2px);
                            box-shadow: 0 6px 16px rgba(0, 86, 214, 0.35);
                        }
                        
                        .footer {
                            margin-top: 40px;
                        }
                        
                        .footer-divider {
                            height: 1px;
                            background: linear-gradient(to right, transparent, var(--border-color), transparent);
                            margin-bottom: 20px;
                        }
                        
                        .footer-content {
                            color: var(--light-text);
                            font-size: 13px;
                            text-align: center;
                            line-height: 1.5;
                        }
                    </style>
                </head>
                <body margin="0" marginwidth="0" marginheight="0" topmargin="0" leftmargin="0" style="margin:0;padding:0;">
                    <div style="display:none;max-height:0px;overflow:hidden;font-size:1px;color:transparent;line-height:1px;">New Passenger Complaint submitted by {{ passenger_name }} on {{ complaint_date }}</div>
                    <div class="container" style="margin:0 auto;padding:0;">
                        <div class="header">
                            <h1>Rail Sathi Complaint Alert</h1>
                            <p>Immediate attention required</p>
                        </div>
                        
                        <div class="content">
                            
                            <div class="complaint-summary">
                                <div class="complaint-id-badge">Complaint #{{ complain_id }}</div>
                                <h2>New Passenger Complaint</h2>
                                <p class="timestamp">Submitted: {{ created_at }}</p>
                            </div>
                            
                            <div class="card">
                                <div class="card-header">
                                    <div class="card-icon">👤</div>
                                    <h3 class="card-title">Passenger Information</h3>
                                </div>
                                <div style="padding: 20px;">
                                <table style="width: 100%; border-collapse: separate; border-spacing: 0;">
                                    <tr>
                                        <td style="padding: 12px 15px; width: 180px; vertical-align: middle; background-color: #f0f7ff; border-radius: 6px 0 0 6px; border-left: 3px solid var(--primary-color);">
                                            <span class="info-label">NAME</span>
                                        </td>
                                        <td style="padding: 12px 15px; vertical-align: middle; background-color: #fafafa; border-radius: 0 6px 6px 0;">
                                            <span class="info-value">{{ passenger_name }}</span>
                                        </td>
                                    </tr>
                                    <tr>
                                        <td style="padding: 12px 15px; width: 180px; vertical-align: middle; background-color: #f0f7ff; border-radius: 6px 0 0 6px; border-left: 3px solid var(--primary-color);">
                                            <span class="info-label">PHONE NUMBER</span>
                                        </td>
                                        <td style="padding: 12px 15px; vertical-align: middle; background-color: #fafafa; border-radius: 0 6px 6px 0;">
                                            <span class="info-value">{{ user_phone_number }}</span>
                                        </td>
                                    </tr>
                                </table>
                                </div>
                            </div>
                            
                            <div class="card">
                                <div class="card-header">
                                    <div class="card-icon">🚆</div>
                                    <h3 class="card-title">Journey Details</h3>
                                </div>
                                <div style="padding: 20px;">
                                <table style="width: 100%; border-collapse: separate; border-spacing: 0 8px;">
                                    <tr>
                                        <td style="padding: 12px 15px; width: 180px; vertical-align: middle; background-color: #f0f7ff; border-radius: 6px 0 0 6px; border-left: 3px solid var(--primary-color);">
                                            <span class="info-label">TRAIN NUMBER</span>
                                        </td>
                                        <td style="padding: 12px 15px; vertical-align: middle; background-color: #fafafa; border-radius: 0 6px 6px 0;">
                                            <span class="info-value">{{ train_no }}</span>
                                        </td>
                                    </tr>
                                    <tr>
                                        <td style="padding: 12px 15px; width: 180px; vertical-align: middle; background-color: #f0f7ff; border-radius: 6px 0 0 6px; border-left: 3px solid var(--primary-color);">
                                            <span class="info-label">TRAIN NAME</span>
                                        </td>
                                        <td style="padding: 12px 15px; vertical-align: middle; background-color: #fafafa; border-radius: 0 6px 6px 0;">
                                            <span class="info-value">{{ train_name }}</span>
                                        </td>
                                    </tr>
                                    <tr>
                                        <td style="padding: 12px 15px; width: 180px; vertical-align: middle; background-color: #f0f7ff; border-radius: 6px 0 0 6px; border-left: 3px solid var(--primary-color);">
                                            <span class="info-label">COACH</span>
                                        </td>
                                        <td style="padding: 12px 15px; vertical-align: middle; background-color: #fafafa; border-radius: 0 6px 6px 0;">
                                            <span class="info-value">{{ coach }}</span>
                                        </td>
                                    </tr>
                                    <tr>
                                        <td style="padding: 12px 15px; width: 180px; vertical-align: middle; background-color: #f0f7ff; border-radius: 6px 0 0 6px; border-left: 3px solid var(--primary-color);">
                                            <span class="info-label">BERTH NUMBER</span>
                                        </td>
                                        <td style="padding: 12px 15px; vertical-align: middle; background-color: #fafafa; border-radius: 0 6px 6px 0;">
                                            <span class="info-value">{{ berth }}</span>
                                        </td>
                                    </tr>
                                    <tr>
                                        <td style="padding: 12px 15px; width: 180px; vertical-align: middle; background-color: #f0f7ff; border-radius: 6px 0 0 6px; border-left: 3px solid var(--primary-color);">
                                            <span class="info-label">PNR</span>
                                        </td>
                                        <td style="padding: 12px 15px; vertical-align: middle; background-color: #fafafa; border-radius: 0 6px 6px 0;">
                                            <span class="info-value">{{ pnr }}</span>
                                        </td>
                                    </tr>
                                    <tr>
                                        <td style="padding: 12px 15px; width: 180px; vertical-align: middle; background-color: #f0f7ff; border-radius: 6px 0 0 6px; border-left: 3px solid var(--primary-color);">
                                            <span class="info-label">TRAIN DEPOT</span>
                                        </td>
                                        <td style="padding: 12px 15px; vertical-align: middle; background-color: #fafafa; border-radius: 0 6px 6px 0;">
                                            <span class="info-value">{{ train_depo }}</span>
                                        </td>
                                    </tr>
                                </table>
                            </div>
                            
                            <div class="card">
                                <div class="card-header">
                                    <div class="card-icon">📝</div>
                                    <h3 class="card-title">Complaint Description</h3>
                                </div>
                                <div class="complaint-description">
                                    <div class="description-box">{{ description }}</div>
                                </div>
                            </div>
                            
                            <div class="button-container">
                                <a href="{{ dashboard_link }}" class="action-button">View in Dashboard</a>
                            </div>
                            
                            <p style="text-align: center; margin-top: 32px; margin-bottom: 20px; color: var(--medium-text); font-size: 15px;">
                                Thank you for your prompt attention to this matter.<br>
                                <span style="font-weight: 600; color: var(--dark-text);">Team Rail Sathi</span>
                            </p>
                        </div>
                        
                        <footer class="footer">
                            <div class="footer-divider"></div>
                            <div class="footer-content">
                                <p>This is an automated notification. Please do not reply to this email.</p>
                                <p>&copy; {{ current_year }} S2 Corporation. All rights reserved.</p>
                            </div>
                        </footer>
                    </div>
                </body>
                </html>
            """
        
        template = Template(template_content)
        message = template.render(context)

        # Create list of unique email addresses for logging
        assigned_user_emails = [user.get('email') for user in assigned_users_list if user.get('email')]
        assigned_user_emails = list(dict.fromkeys(assigned_user_emails))  # Remove duplicates
        
        if assigned_user_emails:
            logging.info(f"Train access users to be notified: {', '.join(assigned_user_emails)}")

        # Send emails to war room users, s2 admins, railway admins, and train access users
        # Create list of unique email addresses for logging
        assigned_user_emails = [user.get('email') for user in assigned_users_list if user.get('email')]
        assigned_user_emails = list(dict.fromkeys(assigned_user_emails))  # Remove duplicates
        
        if assigned_user_emails:
            logging.info(f"Train access users to be notified: {', '.join(assigned_user_emails)}")

        # Send emails to war room users, s2 admins, railway admins, and train access users
        emails_sent = 0
        for user in all_users_to_mail:
            email = user.get('email', '')
        for user in all_users_to_mail:
            email = user.get('email', '')
            if email and not email.startswith("noemail") and '@' in email:
                try:
                    # Use HTML email function instead of plain text
                    success = send_html_mail(subject, message, EMAIL_SENDER, [email])
                    if success:
                        emails_sent += 1
                        logging.info(f"HTML email sent to {email} for complaint {complain_details['complain_id']}")
                    else:
                        logging.error(f"Failed to send HTML email to {email}")
                except Exception as e:
                    logging.error(f"Error sending email to {email}: {e}")

        if not all_users_to_mail:
            logging.info(f"No users found for depot {train_depo} and train {train_no} in complaint {complain_details['complain_id']}")
            return {"status": "success", "message": "No users found for this depot and train"}
        if not all_users_to_mail:
            logging.info(f"No users found for depot {train_depo} and train {train_no} in complaint {complain_details['complain_id']}")
            return {"status": "success", "message": "No users found for this depot and train"}
        
        return {"status": "success", "message": f"Emails sent to {emails_sent} users"}
        
    except Exception as e:
        logging.error(f"Error in send_passenger_complain_email: {e}")
        return {"status": "error", "message": str(e)}
    
    
def execute_sql_query(sql_query: str):
    """Execute a SELECT query safely"""
    if not sql_query.strip().lower().startswith("select"):
        raise ValueError("Only SELECT queries are allowed")

    conn = get_db_connection()
    try:
        results = execute_query(conn, sql_query)
        return results
    finally:
        conn.close()
