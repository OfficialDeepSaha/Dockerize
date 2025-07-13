import os
import io
import logging
import uuid
import threading
import re
from datetime import datetime, date
from typing import List, Dict, Optional, Any
import cloudinary
import cloudinary.uploader
import cloudinary.api
from PIL import Image
from urllib.parse import unquote
from database import get_db_connection, execute_query, execute_query_one
from utils.email_utils import send_plain_mail, send_passenger_complain_email
from dotenv import load_dotenv
from fastapi import FastAPI, Form, File, UploadFile, HTTPException
import asyncio

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

# Cloudinary configuration
cloudinary.config(
    cloud_name=os.getenv('CLOUDINARY_CLOUD_NAME', 'your-cloud-name'),
    api_key=os.getenv('CLOUDINARY_API_KEY', 'your-api-key'),
    api_secret=os.getenv('CLOUDINARY_API_SECRET', 'your-api-secret')
)

def get_valid_filename(filename):
    """
    Replace django.utils.text.get_valid_filename functionality
    """
    filename = re.sub(r'[^\w\s-]', '', filename).strip()
    filename = re.sub(r'[-\s]+', '-', filename)
    return filename

def sanitize_timestamp(raw_timestamp):
    """Sanitize timestamp for filename"""
    decoded = unquote(raw_timestamp)
    return get_valid_filename(decoded).replace(":", "_")

def process_media_file_upload(file_content, file_format, complain_id, media_type):
    """Process and upload media file to Cloudinary"""
    try:
        created_at = datetime.now().strftime("%Y-%m-%d_%H:%M:%S.%f")
        unique_id = str(uuid.uuid4())[:5]
        full_file_name = f"rail_sathi_complain_{complain_id}_{sanitize_timestamp(created_at)}_{unique_id}"
        folder_path = "rail_sathi_complain"

        if media_type == "image":
            # Process image file
            file_stream = io.BytesIO(file_content)
            original_image = Image.open(file_stream)
            if original_image.mode == 'RGBA':
                original_image = original_image.convert('RGB')
            
            # Save to a temporary BytesIO object
            new_file = io.BytesIO()
            original_image.save(new_file, format='JPEG')
            new_file.seek(0)
            
            # Upload to Cloudinary
            upload_result = cloudinary.uploader.upload(
                new_file,
                public_id=f"{folder_path}/images/{full_file_name}",
                resource_type="image",
                folder="rail_sathi_complain_images"
            )
            print(f"Image uploaded to Cloudinary: {full_file_name}")
            return upload_result['secure_url']

        elif media_type == "video":
            try:
                # Create temp directory if it doesn't exist
                temp_dir = "./temp_rail_sathi"
                os.makedirs(temp_dir, exist_ok=True)
                
                # Save the video to a temporary file
                temp_file_path = os.path.join(temp_dir, f"{full_file_name}.{file_format}")
                with open(temp_file_path, 'wb') as temp_file:
                    temp_file.write(file_content)
                
                # Upload to Cloudinary
                upload_result = cloudinary.uploader.upload(
                    temp_file_path,
                    public_id=f"{folder_path}/videos/{full_file_name}",
                    resource_type="video",
                    folder="rail_sathi_complain_videos"
                )
                
                # Clean up temp file
                try:
                    os.remove(temp_file_path)
                except Exception as e:
                    print(f"Error removing temp file: {e}")
                
                print(f"Video uploaded to Cloudinary: {full_file_name}")
                return upload_result['secure_url']
            except Exception as e:
                print(f"Error processing video: {e}")
                raise
        else:
            # For other file types
            temp_dir = "./temp_rail_sathi"
            os.makedirs(temp_dir, exist_ok=True)
            
            # Save to a temporary file
            temp_file_path = os.path.join(temp_dir, f"{full_file_name}.{file_format}")
            with open(temp_file_path, 'wb') as temp_file:
                temp_file.write(file_content)
            
            # Upload to Cloudinary
            upload_result = cloudinary.uploader.upload(
                temp_file_path,
                public_id=f"{folder_path}/files/{full_file_name}",
                resource_type="raw",
                folder="rail_sathi_complain_files"
            )
            
            # Clean up temp file
            try:
                os.remove(temp_file_path)
            except Exception as e:
                print(f"Error removing temp file: {e}")
            
            print(f"File uploaded to Cloudinary: {full_file_name}")
            return upload_result['secure_url']
    except Exception as e:
        print(f"Error uploading file to Cloudinary: {e}")
        raise e

def upload_file_thread(file_obj, complain_id, user):
    """Upload file in a separate thread with improved error handling"""
    try:
        logger.info(f"Starting file upload for complaint {complain_id}, file: {getattr(file_obj, 'filename', 'unknown')}")
        
        # Read file content - handle both FastAPI UploadFile and regular file objects
        if hasattr(file_obj, 'read'):
            if asyncio.iscoroutinefunction(file_obj.read):
                # For async UploadFile, we need to handle this differently
                logger.error("Async file read not supported in thread context")
                return
            file_content = file_obj.read()
        else:
            file_content = file_obj.file.read()
        
        logger.info(f"File content size: {len(file_content)} bytes")
        
        filename = getattr(file_obj, 'filename', 'unknown')
        content_type = getattr(file_obj, 'content_type', 'application/octet-stream')
        
        logger.info(f"Processing file: {filename}, content_type: {content_type}")
        
        _, ext = os.path.splitext(filename)
        ext = ext.lstrip('.').lower()
        
        # Determine media type
        if content_type.startswith("image"):
            media_type = "image"
        elif content_type.startswith("video"):
            media_type = "video"
        else:
            logger.warning(f"Unsupported media type for file: {filename}, content_type: {content_type}")
            return

        logger.info(f"Uploading {media_type} file: {filename}")
        
        # Upload file
        uploaded_url = process_media_file_upload(file_content, ext, complain_id, media_type)
        
        if uploaded_url:
            logger.info(f"File uploaded successfully: {uploaded_url}")
            
            # Insert media record into database
            conn = get_db_connection()
            try:
                query = """
                    INSERT INTO rail_sathi_complain_media 
                    (complain_id, media_type, media_url, created_by, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """
                now = datetime.now()
                cursor = conn.cursor()
                cursor.execute(query, (complain_id, media_type, uploaded_url, user, now, now))
                conn.commit()
                logger.info(f"Media record created successfully for complaint {complain_id}")
            except Exception as db_error:
                logger.error(f"Database error while saving media record: {db_error}")
                conn.rollback()
            finally:
                conn.close()
        else:
            logger.error(f"File upload failed for complaint {complain_id}: {filename}")
            
    except Exception as e:
        logger.error(f"Error in upload_file_thread for file {getattr(file_obj, 'filename', 'unknown')}: {e}")
        import traceback
        logger.error(f"Full traceback: {traceback.format_exc()}")

async def upload_file_async(file_obj: UploadFile, complain_id: int, user: str):
    """Async version of file upload"""
    try:
        logger.info(f"Starting async file upload for complaint {complain_id}, file: {file_obj.filename}")
        
        # Read file content asynchronously
        file_content = await file_obj.read()
        logger.info(f"File content size: {len(file_content)} bytes")
        
        filename = file_obj.filename
        content_type = file_obj.content_type
        
        logger.info(f"Processing file: {filename}, content_type: {content_type}")
        
        _, ext = os.path.splitext(filename)
        ext = ext.lstrip('.').lower()
        
        # Determine media type
        if content_type.startswith("image"):
            media_type = "image"
        elif content_type.startswith("video"):
            media_type = "video"
        else:
            logger.warning(f"Unsupported media type for file: {filename}, content_type: {content_type}")
            return False

        logger.info(f"Uploading {media_type} file: {filename}")
        
        # Upload file
        uploaded_url = process_media_file_upload(file_content, ext, complain_id, media_type)
        
        if uploaded_url:
            logger.info(f"File uploaded successfully: {uploaded_url}")
            
            # Insert media record into database
            conn = get_db_connection()
            try:
                query = """
                    INSERT INTO rail_sathi_complain_media 
                    (complain_id, media_type, media_url, created_by, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """
                now = datetime.now()
                cursor = conn.cursor()
                cursor.execute(query, (complain_id, media_type, uploaded_url, user, now, now))
                conn.commit()
                logger.info(f"Media record created successfully for complaint {complain_id}")
                return True
            except Exception as db_error:
                logger.error(f"Database error while saving media record: {db_error}")
                conn.rollback()
                return False
            finally:
                conn.close()
        else:
            logger.error(f"File upload failed for complaint {complain_id}: {filename}")
            return False
            
    except Exception as e:
        logger.error(f"Error in upload_file_async for file {file_obj.filename}: {e}")
        import traceback
        logger.error(f"Full traceback: {traceback.format_exc()}")
        return False

# Test function to verify setup
def test_gcs_connection():
    """Test GCS connection with .env configuration"""
    try:
        print("=== Testing GCS Connection ===")
        print(f"Project ID: {PROJECT_ID}")
        print(f"Bucket Name: {GCS_BUCKET_NAME}")
        print(f"Credentials Path: {os.getenv('GOOGLE_APPLICATION_CREDENTIALS')}")
        
        client = get_gcs_client()
        bucket = client.bucket(GCS_BUCKET_NAME)
        bucket.reload()  # This will fail if no access
        
        print(f"✓ Successfully connected to bucket: {GCS_BUCKET_NAME}")
        print(f"✓ Bucket location: {bucket.location}")
        print(f"✓ Bucket storage class: {bucket.storage_class}")
        return True
    except Exception as e:
        print(f"✗ Failed to connect to GCS bucket: {e}")
        return False
    
def validate_and_process_train_data(complaint_data):
    """Validate and process train data in complaint"""
    # Skip train details lookup since trains_traindetails table doesn't exist
    # Just use the provided train information directly
    
    # Ensure train_number is a string
    if complaint_data.get('train_number'):
        complaint_data['train_number'] = str(complaint_data['train_number'])
    
    # If train_name is not provided but train_number is, set a default name
    if complaint_data.get('train_number') and not complaint_data.get('train_name'):
        complaint_data['train_name'] = f"Train #{complaint_data['train_number']}"
    
    # No need for database connection since we're not querying
    return complaint_data

def create_complaint(complaint_data):
    """Create a new complaint"""
    conn = get_db_connection()
    try:
        # Validate and process train data
        complaint_data = validate_and_process_train_data(complaint_data)

        # Handle date_of_journey - use current date if not provided or invalid
        date_of_journey_str = complaint_data.get('date_of_journey')
        if date_of_journey_str:
            try:
                date_of_journey = datetime.strptime(date_of_journey_str, "%Y-%m-%d")
            except (ValueError, TypeError):
                # If date format is invalid, use current date
                date_of_journey = datetime.now()
        else:
            # If date is None or empty, use current date
            date_of_journey = datetime.now()

        # Handle complain_date
        complain_date = complaint_data.get('complain_date')
        if isinstance(complain_date, str):
            try:
                complain_date = datetime.strptime(complain_date, '%Y-%m-%d').date()
            except ValueError:
                complain_date = date.today()
        elif complain_date is None:
            complain_date = date.today()
            
        
        # Insert complaint - PostgreSQL version with RETURNING clause
        query = """
            INSERT INTO rail_sathi_complain 
            (pnr_number, is_pnr_validated, name, mobile_number, complain_type, 
             complain_description, complain_date, complain_status, train_id, 
             train_number, train_name, coach, berth_no, created_by, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING complain_id
        """
        now = datetime.now()
        cursor = conn.cursor()
        cursor.execute(query, (
            complaint_data.get('pnr_number'),
            complaint_data.get('is_pnr_validated', 'not-attempted'),
            complaint_data.get('name'),
            complaint_data.get('mobile_number'),
            complaint_data.get('complain_type'),
            complaint_data.get('complain_description'),
            complain_date,
            complaint_data.get('complain_status', 'pending'),
            complaint_data.get('train_id'),
            complaint_data.get('train_number'),
            complaint_data.get('train_name'),
            complaint_data.get('coach'),
            complaint_data.get('berth_no'),
            complaint_data.get('created_by'),
            now,
            now
        ))
        
        complain_id = cursor.fetchone()[0]
        conn.commit()
        
        # Get the created complaint
        complaint = get_complaint_by_id(complain_id)
        
        # Send email in separate thread
        def _send_email(complaint_data, complaint_id):
            try:
                logger.info(f"Email thread started for complaint {complaint_id}")
                
                train_depo = ''
                if complaint_data.get('train_id'):
                    train_query = "SELECT * FROM trains_traindetails WHERE id = %s"
                    train_conn = get_db_connection()
                    train = execute_query_one(train_conn, train_query, (complaint_data['train_id'],))
                    train_conn.close()
                    if train:
                        train_depo = train.get('Depot', '')
                elif complaint_data.get('train_number'):
                    train_query = "SELECT * FROM trains_traindetails WHERE train_no = %s"
                    train_conn = get_db_connection()
                    train = execute_query_one(train_conn, train_query, (complaint_data['train_number'],))
                    train_conn.close()
                    if train:
                        train_depo = train.get('Depot', '')
                
                details = {
                    'train_no': complaint_data.get('train_number', ''),
                    'train_name': complaint_data.get('train_name', ''),
                    'user_phone_number': complaint_data.get('mobile_number', ''),
                    'passenger_name': complaint_data.get('name', ''),
                    'pnr': complaint_data.get('pnr_number', ''),
                    'berth': complaint_data.get('berth_no', ''),
                    'coach': complaint_data.get('coach', ''),
                    'complain_id': complaint_id,
                    'description': complaint_data.get('complain_description', ''),
                    'train_depo': train_depo,
                    'date_of_journey': date_of_journey.strftime("%d %b %Y"),
                }
                
                logger.info(f"Sending email for complaint {complaint_id} to war room users")
                send_passenger_complain_email(details)
                logger.info(f"Email sent successfully for complaint {complaint_id}")
            except Exception as e:
                logger.error(f"Email thread failure for complaint {complaint_id}: {str(e)}")
        
        try:
            email_thread = threading.Thread(
                target=_send_email,
                args=(complaint_data, complain_id),
                name=f"EmailThread-{complain_id}"
            )
            email_thread.daemon = True
            logger.info(f"Starting email thread for complaint {complain_id}")
            email_thread.start()
            logger.info(f"Email thread started with name {email_thread.name}")
        except Exception as e:
            logger.error(f"Failed to create email thread: {str(e)}")
        
        return complaint
    finally:
        conn.close()

def get_complaint_by_id(complain_id: int):
    """Get complaint by ID with media files"""
    conn = get_db_connection()
    try:
        # Get complaint
        query = """
            SELECT c.*, t.train_no, COALESCE(t.train_name, c.train_name) AS train_name, t."Depot" as train_depot
            FROM rail_sathi_complain c
            LEFT JOIN trains_traindetails t ON c.train_id = t.id
            WHERE c.complain_id = %s
        """
        complaint = execute_query_one(conn, query, (complain_id,))
        
        if not complaint:
            return None
        
        # Get media files
        media_query = """
            SELECT id, media_type, media_url, created_at, updated_at, created_by, updated_by
            FROM rail_sathi_complain_media
            WHERE complain_id = %s
        """
        media_files = execute_query(conn, media_query, (complain_id,))
        
        # Format response
        complaint['rail_sathi_complain_media_files'] = media_files or []
        return complaint
    finally:
        conn.close()

def get_complaints_by_date(complain_date: date, mobile_number: str):
    """Get complaints by date and mobile number"""
    conn = get_db_connection()
    try:
        query = """
            SELECT c.*, t.train_no, COALESCE(t.train_name, c.train_name) AS train_name, t."Depot" as train_depot
            FROM rail_sathi_complain c
            LEFT JOIN trains_traindetails t ON c.train_id = t.id
            WHERE c.complain_date = %s AND c.mobile_number = %s
        """
        complaints = execute_query(conn, query, (complain_date, mobile_number))
        
        # Get media files for each complaint
        for complaint in complaints:
            media_query = """
                SELECT id, media_type, media_url, created_at, updated_at, created_by, updated_by
                FROM rail_sathi_complain_media
                WHERE complain_id = %s
            """
            media_files = execute_query(conn, media_query, (complaint['complain_id'],))
            complaint['rail_sathi_complain_media_files'] = media_files or []
        
        return complaints
    finally:
        conn.close()

def update_complaint(complain_id: int, update_data: dict):
    """Update complaint"""
    conn = get_db_connection()
    try:
        # Validate and process train data
        update_data = validate_and_process_train_data(update_data)
        
        # Parse complain_date if it's a string
        if 'complain_date' in update_data and isinstance(update_data['complain_date'], str):
            try:
                update_data['complain_date'] = datetime.strptime(update_data['complain_date'], '%Y-%m-%d').date()
            except ValueError:
                pass  # Keep original value if parsing fails
        
        # Build dynamic update query
        update_fields = []
        values = []
        
        allowed_fields = [
            'pnr_number', 'is_pnr_validated', 'name', 'mobile_number', 
            'complain_type', 'complain_description', 'complain_date', 
            'complain_status', 'train_id', 'train_number', 'train_name', 
            'coach', 'berth_no', 'updated_by'
        ]
        
        for field in allowed_fields:
            if field in update_data:
                update_fields.append(f"{field} = %s")
                values.append(update_data[field])
        
        if not update_fields:
            return get_complaint_by_id(complain_id)
        
        # Add updated_at
        update_fields.append("updated_at = %s")
        values.append(datetime.now())
        values.append(complain_id)
        
        query = f"""
            UPDATE rail_sathi_complain 
            SET {', '.join(update_fields)}
            WHERE complain_id = %s
        """
        
        cursor = conn.cursor()
        cursor.execute(query, tuple(values))
        conn.commit()
        
        return get_complaint_by_id(complain_id)
    finally:
        conn.close()

def delete_complaint(complain_id: int):
    """Delete complaint and its media files"""
    conn = get_db_connection()
    try:
        # First delete media files
        cursor = conn.cursor()
        cursor.execute("DELETE FROM rail_sathi_complain_media WHERE complain_id = %s", (complain_id,))
        
        # Then delete complaint
        cursor.execute("DELETE FROM rail_sathi_complain WHERE complain_id = %s", (complain_id,))
        deleted_count = cursor.rowcount
        conn.commit()
        
        return deleted_count
    finally:
        conn.close()

def delete_complaint_media(complain_id: int, media_ids: List[int]):
    """Delete specific media files from complaint"""
    conn = get_db_connection()
    try:
        if not media_ids:
            return 0
        
        # PostgreSQL uses ANY() for IN clause with arrays
        query = """
            DELETE FROM rail_sathi_complain_media 
            WHERE complain_id = %s AND id = ANY(%s)
        """
        
        cursor = conn.cursor()
        cursor.execute(query, (complain_id, media_ids))
        deleted_count = cursor.rowcount
        conn.commit()
        
        return deleted_count
    finally:
        conn.close()

def validate_complaint_access(complain_id: int, user_name: str, mobile_number: str):
    """Validate if user can access/modify the complaint"""
    conn = get_db_connection()
    try:
        query = """
            SELECT created_by, mobile_number, complain_status 
            FROM rail_sathi_complain 
            WHERE complain_id = %s
        """
        complaint = execute_query_one(conn, query, (complain_id,))
        
        if not complaint:
            return False, "Complaint not found"
        
        if (complaint['created_by'] != user_name or 
            complaint['mobile_number'] != mobile_number or 
            complaint['complain_status'] == "completed"):
            return False, "Only user who created the complaint can update it."
        
        return True, None
    finally:
        conn.close()