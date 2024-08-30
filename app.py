from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_cors import CORS  # Import the CORS library
import os
import sqlite3

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Directory to save uploaded files
UPLOAD_FOLDER = 'D:/my_fresh_flask_blog/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

DATABASE = 'D:/my_fresh_flask_blog/data.db'

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS posts
                          (id INTEGER PRIMARY KEY, text TEXT, image TEXT)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS comments
                          (id INTEGER PRIMARY KEY, post_id INTEGER, text TEXT, 
                           parent_id INTEGER, FOREIGN KEY(post_id) REFERENCES posts(id))''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS reactions
                          (id INTEGER PRIMARY KEY, post_id INTEGER, comment_id INTEGER, 
                           reaction_type TEXT, FOREIGN KEY(post_id) REFERENCES posts(id), 
                           FOREIGN KEY(comment_id) REFERENCES comments(id))''')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    file = request.files.get('file')
    if not file or file.filename == '':
        return jsonify({"error": "No file selected"}), 400

    file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
    file.save(file_path)

    return jsonify({"message": "File uploaded successfully", "filename": file.filename}), 200

@app.route('/save-posts', methods=['POST'])
def save_posts():
    posts = request.json.get('posts', [])
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM posts")
        cursor.execute("DELETE FROM comments")
        cursor.execute("DELETE FROM reactions")
        
        for post in posts:
            cursor.execute("INSERT INTO posts (id, text, image) VALUES (?, ?, ?)", 
                           (post['id'], post['text'], post.get('image')))
            for comment in post.get('comments', []):
                cursor.execute("INSERT INTO comments (id, post_id, text, parent_id) VALUES (?, ?, ?, ?)", 
                               (comment['id'], post['id'], comment['text'], comment.get('parent_id')))
                for reply in comment.get('replies', []):
                    cursor.execute("INSERT INTO comments (id, post_id, text, parent_id) VALUES (?, ?, ?, ?)", 
                                   (reply['id'], post['id'], reply['text'], comment['id']))
            for reaction_type, count in post.get('reactions', {}).items():
                cursor.execute("INSERT INTO reactions (post_id, reaction_type) VALUES (?, ?)", 
                               (post['id'], reaction_type))
                
    return jsonify({"message": "Posts saved successfully"}), 200

@app.route('/load-posts', methods=['GET'])
def load_posts():
    posts_data = []
    with get_db() as conn:
        cursor = conn.cursor()
        posts = cursor.execute("SELECT * FROM posts").fetchall()
        for post in posts:
            post_dict = {"id": post["id"], "text": post["text"], "image": post["image"], "reactions": {}, "comments": []}
            
            reactions = cursor.execute("SELECT reaction_type, COUNT(*) as count FROM reactions WHERE post_id = ? GROUP BY reaction_type", 
                                       (post["id"],)).fetchall()
            for reaction in reactions:
                post_dict["reactions"][reaction["reaction_type"]] = reaction["count"]
            
            comments = cursor.execute("SELECT * FROM comments WHERE post_id = ? AND parent_id IS NULL", 
                                      (post["id"],)).fetchall()
            for comment in comments:
                comment_dict = {"id": comment["id"], "text": comment["text"], "reactions": {}, "replies": []}
                
                comment_reactions = cursor.execute("SELECT reaction_type, COUNT(*) as count FROM reactions WHERE comment_id = ? GROUP BY reaction_type", 
                                                   (comment["id"],)).fetchall()
                for reaction in comment_reactions:
                    comment_dict["reactions"][reaction["reaction_type"]] = reaction["count"]
                
                replies = cursor.execute("SELECT * FROM comments WHERE parent_id = ?", 
                                         (comment["id"],)).fetchall()
                for reply in replies:
                    reply_dict = {"id": reply["id"], "text": reply["text"], "reactions": {}}
                    
                    reply_reactions = cursor.execute("SELECT reaction_type, COUNT(*) as count FROM reactions WHERE comment_id = ? GROUP BY reaction_type", 
                                                     (reply["id"],)).fetchall()
                    for reaction in reply_reactions:
                        reply_dict["reactions"][reaction["reaction_type"]] = reaction["count"]
                    
                    comment_dict["replies"].append(reply_dict)
                
                post_dict["comments"].append(comment_dict)
            
            posts_data.append(post_dict)
    
    return jsonify(posts_data), 200

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
    init_db()  # Initialize the database before starting the app

    # Ensure you have cert.pem and key_nopass.pem in your project directory.
    app.run(debug=True, host='0.0.0.0', port=5000, ssl_context=('cert.pem', 'key_nopass.pem'))
