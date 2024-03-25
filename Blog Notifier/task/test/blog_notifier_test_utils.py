import http.server
import http.server
import os
import random
import shutil
import socket
import socketserver
from string import Template

NO_LINKS_TEST = 'no_links'
FLAT_MULTIPLE_LINKS_TEST = 'flat_multiple_links'
NESTED_LINKS_TEST = 'nested_links'
NESTED_AND_FLAT_LINKS_TEST = 'nested_and_flat_links'
CYCLIC_LINKS_TEST = 'cyclic_reference'

FAKE_BLOG = "fake-blog"
PORT = 8000
ADDRESS = "127.0.0.1"
blog_addr = f"http://{ADDRESS}:{PORT}/{FAKE_BLOG}/"
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


# def remove_html_files():
#     for file_name in html_files:
#         if os.path.exists(file_name):
#             os.remove(file_name)


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
def create_blog_site_with_nested_posts(depth: int, test_name=NESTED_LINKS_TEST):
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
    nested_post_2 = create_blog_site_with_nested_posts(depth=2, test_name='nested_links_2')
    t = Template(link_template)
    l += t.substitute({'postaddr': f"{blog_addr}{nested_post_2}.html", 'name': nested_post_2})
    blog_files[NESTED_AND_FLAT_LINKS_TEST].extend(blog_files['nested_links_2'][-1::-1])
    # visualize_nested_blogs(blog_files['nested_links_2'][-1::-1], 'nested_links_2.txt')

    # creating blog posts with nested links of depth 3
    nested_post_3 = create_blog_site_with_nested_posts(depth=3, test_name='nested_links_3')
    t = Template(link_template)
    l += t.substitute({'postaddr': f"{blog_addr}{nested_post_3}.html", 'name': nested_post_3})
    blog_files[NESTED_AND_FLAT_LINKS_TEST].extend(blog_files['nested_links_3'][-1:-4:-1])
    # visualize_nested_blogs(blog_files['nested_links_3'][-1::-1], 'nested_links_3.txt')

    # creating blog posts with nested links of depth 4
    nested_post_4 = create_blog_site_with_nested_posts(depth=4, test_name='nested_links_4')
    t = Template(link_template)
    l += t.substitute({'postaddr': f"{blog_addr}{nested_post_4}.html", 'name': nested_post_4})
    blog_files[NESTED_AND_FLAT_LINKS_TEST].extend(blog_files['nested_links_4'][-1:-4:-1])
    # visualize_nested_blogs(blog_files['nested_links_4'][-1::-1], 'nested_links_4.txt')

    t = Template(page_template)
    blog_page = t.substitute({'body': l})
    create_html_file("index2.html", blog_page)
    html_files.append("index2.html")
    blog_files[NESTED_AND_FLAT_LINKS_TEST].append(f'{blog_addr}index2.html')


# this would create a blog site with the following pattern: a.html has link for b.html, b.html has link for a.html
# and c.html, c.html does not have any hyperlinks
def create_blog_with_cyclic_reference():
    blog_files[CYCLIC_LINKS_TEST] = []
    # creating c.html, notice it does not contain any hyperlinks
    c_html = generate_random_text(k=4)
    create_html_file(f'{c_html}.html',
                     Template(page_template).substitute(
                         {'body': f'<div class="post"><p>{generate_random_text(250)}</p></div>'}))
    html_files.append(f'{c_html}.html')
    blog_files[CYCLIC_LINKS_TEST].append(f'{blog_addr}{c_html}.html')

    a_html = generate_random_text(k=4)
    b_html = generate_random_text(k=4)

    # body for a.html, notice it contains link for b.html
    t_a = Template(link_template)
    l_a = t_a.substitute({'postaddr': f'{blog_addr}{b_html}.html', 'name': b_html})

    # body for b.html, notice it contains link for a.html and c.html
    t_b = Template(link_template)
    l_b = t_b.substitute({'postaddr': f'{blog_addr}{c_html}.html', 'name': c_html})
    l_b += t_b.substitute({'postaddr': f'{blog_addr}{a_html}.html', 'name': a_html})

    # creating b.html
    create_html_file(f'{b_html}.html',
                     Template(page_template).substitute(
                         {'body': l_b}))
    html_files.append(f'{b_html}.html')
    blog_files[CYCLIC_LINKS_TEST].append(f'{blog_addr}{b_html}.html')

    # creating a.html
    create_html_file(f'{a_html}.html',
                     Template(page_template).substitute(
                         {'body': l_a}))
    html_files.append(f'{a_html}.html')
    blog_files[CYCLIC_LINKS_TEST].append(f'{blog_addr}{a_html}.html')


def create_blog_site_with_duplicate_links():
    index_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Random Blog Post</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            line-height: 1.6;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
        }}
        .post {{
            margin-bottom: 20px;
            border: 1px solid #ccc;
            padding: 15px;
            border-radius: 8px;
            background-color: #fff;
        }}

        h1 {{
            color: #333;
        }}

        p {{
            color: #666;
        }}

        a {{
            color: #007BFF;
            text-decoration: none;
            font-weight: bold;
        }}

        a:hover {{
            text-decoration: underline;
        }}
    </style>
</head>
<body>
    <div class="post">
        <h2> <a href="{blog_addr}a.html">This is blog post A</a></h2>
        <p>This is the content of Blog Post A.</p>
    </div>
    <div class="post">
        <h2> <a href="{blog_addr}b.html">This is blog post B</a></h2>
        <p>This is the content of Blog Post B.</p>
    </div>
    <div class="post">
        <h2> <a href="{blog_addr}c.html">This is blog post C</a></h2>
        <p>This is the content of Blog Post C.</p>
    </div>
    <div class="post">
        <h2> <a href="{blog_addr}d.html">This is blog post D</a></h2>
        <p>This is the content of Blog Post D.</p>
    </div>
    <div class="post">
        <h2><a href="{blog_addr}e.html">This is blog post E</a></h2>
        <p>This is the content of Blog Post E.</p>
    </div>
    <div class="post">
        <h2><a href="{blog_addr}f.html">This is blog post F</a></h2>
        <p>This is the content of Blog Post F.</p>
    </div>
    <div class="post">
        <h2><a href="{blog_addr}a.html">Blog Post A Title</a></h2>
        <p>This is the content of Blog Post A.</p>
    </div>
</body>
</html>
"""

    # Create individual blog post content
    post_content = """
    <html>
    <head>
        <title>Blog Post {char}</title>
    </head>
    <body>
        <h1>This is blog post {char}</h1>
        <p>This is the content of Blog Post {char}.</p>
    </body>
    </html>
    """

    blog_files['duplicate_links'] = [
        f"{blog_addr}a.html",
        f"{blog_addr}b.html",
        f"{blog_addr}c.html",
        f"{blog_addr}d.html",
        f"{blog_addr}e.html",
        f"{blog_addr}f.html",
        blog_addr
    ]

    create_html_file("index.html", index_content)

    # Create individual blog post files
    for char in ['a', 'b', 'c', 'd', 'e', 'f']:
        create_html_file(f"{char}.html", post_content.format(char=char))


def run_http_server(port):
    # Create an HTTP server with the specified port and handler
    handler = http.server.SimpleHTTPRequestHandler

    # Create a TCPServer instance with the specified port and handler
    with socketserver.TCPServer(("", port), handler) as httpd:
        # Set SO_REUSEADDR option to allow immediate reuse of the port
        httpd.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        print(f"Serving on port {port}")
        httpd.serve_forever()
