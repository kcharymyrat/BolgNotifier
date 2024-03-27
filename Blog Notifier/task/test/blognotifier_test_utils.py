import random, os, socketserver, http.server, shutil, sqlite3
from string import Template

DB_FILE = 'blogs.sqlite3'
NO_LINKS_TEST = 'no_links'
FLAT_MULTIPLE_LINKS_TEST = 'flat_multiple_links'
NESTED_LINKS_TEST_1 = 'nested_links_1'
NESTED_LINKS_TEST_2 = 'nested_links_2'
NESTED_AND_FLAT_LINKS_TEST = 'nested_and_flat_links'

FAKE_BLOG = "fake-blog"
PORT = 8000
ADDRESS = "127.0.0.1"
blog_addr = f"http://{ADDRESS}:{PORT}/{FAKE_BLOG}/"

tables_properties = {
    'blogs': {
        'site': 'TEXT',
        'last_link': 'TEXT'
    },
    'posts': {
        'link': 'TEXT',
        'site': 'TEXT',
    },
    'mails': {
        'id': 'INTEGER',
        'mail': 'TEXT',
        'is_sent': 'INTEGER'
    }
}

page_template = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Random Blog Post</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            line-height: 1.6;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
        }
        .post {
            margin-bottom: 20px;
            border: 1px solid #ccc;
            padding: 15px;
            border-radius: 8px;
            background-color: #fff;
        }

        h1 {
            color: #333;
        }

        p {
            color: #666;
            word-break: break-all;
            white-space: normal;
        }

        a {
            color: #007BFF;
            text-decoration: none;
            font-weight: bold;
        }

        a:hover {
            text-decoration: underline;
        }
    </style>
</head>
<body>
    $body        
</body>
</html>"""

link_template = """<div class="post">
    <p><a href="$postaddr">$name</a></p>
</div>"""

post_template = """<div class="post">
        <p>$body</p>
    </div>"""

html_files = []
blog_files = {}


def check_table_exists(table_name: str) -> bool:
    connection = sqlite3.connect(DB_FILE)  # Replace 'your_database.db' with your database file
    # Create a cursor object
    cursor = connection.cursor()
    cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}'")
    # Fetch the result
    result = cursor.fetchone()
    cursor.close()
    connection.close()
    return result is not None


def check_table_properties(table_name) -> tuple:
    # Connect to the SQLite database
    connection = sqlite3.connect(DB_FILE)
    # Create a cursor object
    cursor = connection.cursor()
    cursor.execute(f"PRAGMA table_info({table_name})")
    # Fetch all the rows from the result
    columns_info = cursor.fetchall()
    # Convert fetched data into a dictionary {column_name: column_type}
    columns_info_dict = {column[1]: column[2].upper() for column in columns_info}  # Convert types to uppercase
    cursor.close()
    connection.close()

    # Define columns automatically added by GORM that should be ignored
    gorm_columns = {'created_at', 'updated_at', 'deleted_at'}

    # Optionally include 'id' in gorm_columns if it's not a strict requirement
    if 'id' not in tables_properties[table_name]:
        gorm_columns.add('id')

    # Filter out the GORM-specific columns and optionally 'id' from the columns_info_dict
    filtered_columns_info = {k: v for k, v in columns_info_dict.items() if k not in gorm_columns}

    # Check if all required columns and their types exist in the filtered table structure
    required_columns = tables_properties[table_name]
    for col_name, col_type in required_columns.items():
        # Check presence and type of required columns, comparing types in uppercase
        if col_name not in filtered_columns_info or filtered_columns_info[col_name] != col_type.upper():
            # If a required column is missing or has a different type, return False with found columns info
            return False, filtered_columns_info

    # If all required columns are present and have correct types, return True with the filtered columns info
    return True, filtered_columns_info


def remove_db_file():
    print(os.curdir)
    if os.path.exists(DB_FILE):
        os.remove(DB_FILE)


def remove_fake_blog():
    folder_path = os.path.join(os.getcwd(), FAKE_BLOG)
    shutil.rmtree(folder_path)


def create_html_file(file_name, content):
    folder_path = os.path.join(os.getcwd(), FAKE_BLOG)
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
    file_path = os.path.join(folder_path, file_name)
    with open(file_path, 'w') as file:
        file.write(content)


def generate_random_text(k: int) -> str:
    return "".join(random.choices("abcdefghijklmnopqrstuvwxyz123456789", k=k))


# only one html file containing no links will be created
def create_blog_site_with_no_posts():
    name = generate_random_text(4)
    body = f'<div class="post"><p>{generate_random_text(250)}</p></div>'
    t = Template(page_template)
    blog_page = t.substitute({'body': body})
    create_html_file(f'{name}.html', blog_page)
    html_files.append(f'{name}.html')
    blog_files[NO_LINKS_TEST] = f'{blog_addr}{name}.html'


# this will create a website with the following pattern, index.html will contain links to multiple blog posts.
# these blog posts will not contain any links thus, the site created has a flat structure
def create_flat_blog_site_with_multiple_posts():
    n = random.randint(3, 5)
    l = ""
    blog_files['flat_multiple_links'] = []
    for i in range(n):
        name = generate_random_text(k=4)
        postaddr = f"{blog_addr}{name}.html"
        t = Template(link_template)
        l += t.substitute({'postaddr': postaddr, 'name': name})
        create_html_file(f'{name}.html',
                         Template(page_template).substitute(
                             {'body': f'<div class = "post"><p>{generate_random_text(250)}</p></div>'}))
        html_files.append(f'{name}.html')
        blog_files[FLAT_MULTIPLE_LINKS_TEST].append(f'{blog_addr}{name}.html')

    t = Template(page_template)
    blog_page = t.substitute({'body': l})
    create_html_file("index.html", blog_page)
    html_files.append("index.html")
    blog_files[FLAT_MULTIPLE_LINKS_TEST].append(blog_addr)


def _create_blog_site_with_nested_posts(depth: int, test_name):
    if depth == 1:
        name0 = generate_random_text(k=4)
        create_html_file(f'{name0}.html',
                         Template(page_template).substitute(
                             {'body': f'<div class="post"><p>{generate_random_text(250)}</p></div>'}))
        html_files.append(f'{name0}.html')
        blog_files[test_name].append(f'{blog_addr}{name0}.html')
        t = Template(link_template)
        l = t.substitute({'postaddr': f'{blog_addr}{name0}.html', 'name': name0})
        name1 = generate_random_text(k=4)
        create_html_file(f'{name1}.html', Template(page_template).substitute({'body': l}))
        html_files.append(f'{name1}.html')
        blog_files[test_name].append(f'{blog_addr}{name1}.html')
        return name1
    name0 = _create_blog_site_with_nested_posts(depth - 1, test_name)
    t = Template(link_template)
    l = t.substitute({'postaddr': f'{blog_addr}{name0}.html', 'name': name0})
    name1 = generate_random_text(k=4)
    create_html_file(f'{name1}.html', Template(page_template).substitute({'body': l}))
    html_files.append(f'{name1}.html')
    blog_files[test_name].append(f'{blog_addr}{name1}.html')
    return name1


# this will create website with the following pattern: a.html contains link to b.html, b.html contains link to
# c.html, c.html contain link to d.html. depending on the parameter depth, this is created for the test to ensure
# that the blog crawler does not go into endless recursion.
def create_blog_site_with_nested_posts(depth: int, test_name: str):
    blog_files[test_name] = []
    parent_name = _create_blog_site_with_nested_posts(depth, test_name)
    return parent_name


# a blog with the following pattern will be created: a blog site with links to multiple blog posts, Some of these
# blog posts can have nested links. some blog posts have nested and others have flat pattern
def create_blog_site_with_nested_and_flat_posts():
    def visualize_nested_blogs(blog_posts_list: list, viz_file_name: str):
        l = ""
        n = 0
        for el in blog_posts_list:
            l += f'{" " * n}{el}\n'
            n += 1
        with open(viz_file_name, 'w') as f:
            f.write(l)

    blog_files[NESTED_AND_FLAT_LINKS_TEST] = []
    # creating blog posts with no links in them
    n = random.randint(3, 5)
    l = ""
    for i in range(n):
        name = generate_random_text(k=4)
        postaddr = f"{blog_addr}{name}.html"
        t = Template(link_template)
        l += t.substitute({'postaddr': postaddr, 'name': name})
        create_html_file(f'{name}.html',
                         Template(page_template).substitute(
                             {'body': f'<div class = "post"><p>{generate_random_text(250)}</p></div>'}))
        html_files.append(f'{name}.html')
        blog_files[NESTED_AND_FLAT_LINKS_TEST].append(postaddr)

    # creating blog posts with nested links of depth 2
    nested_post_1 = create_blog_site_with_nested_posts(depth=1, test_name='nested_links_1')
    t = Template(link_template)
    l += t.substitute({'postaddr': f"{blog_addr}{nested_post_1}.html", 'name': nested_post_1})
    blog_files[NESTED_AND_FLAT_LINKS_TEST].extend(blog_files['nested_links_1'][-1::-1])
    # visualize_nested_blogs(blog_files['nested_links_2'][-1::-1], 'nested_links_2.txt')

    # creating blog posts with nested links of depth 3
    nested_post_2 = create_blog_site_with_nested_posts(depth=2, test_name='nested_links_2')
    t = Template(link_template)
    l += t.substitute({'postaddr': f"{blog_addr}{nested_post_2}.html", 'name': nested_post_2})
    blog_files[NESTED_AND_FLAT_LINKS_TEST].extend(blog_files['nested_links_2'][-1::-1])
    # visualize_nested_blogs(blog_files['nested_links_3'][-1::-1], 'nested_links_3.txt')

    t = Template(page_template)
    blog_page = t.substitute({'body': l})
    create_html_file("index2.html", blog_page)
    html_files.append("index2.html")
    blog_files[NESTED_AND_FLAT_LINKS_TEST].append(f'{blog_addr}index2.html')


def run_http_server(port):
    # Create an HTTP server with the specified port and handler
    handler = http.server.SimpleHTTPRequestHandler
    with socketserver.TCPServer(("", port), handler) as httpd:
        print(f"Serving on port {port}")
        httpd.serve_forever()
