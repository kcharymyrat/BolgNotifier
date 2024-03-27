import multiprocessing

from test.tests import TestBlogNotifierCLI
from test.blognotifier_test_utils import *

if __name__ == '__main__':
    http_server_process: multiprocessing.Process = None
    try:
        # creating fake blog(just html files) for testing
        create_blog_site_with_no_posts()
        create_blog_site_with_nested_posts(1, NESTED_LINKS_TEST_1)
        create_blog_site_with_nested_posts(2, NESTED_LINKS_TEST_2)
        create_flat_blog_site_with_multiple_posts()
        create_blog_site_with_nested_and_flat_posts()

        # starting python's http.server
        http_server_process = multiprocessing.Process(target=run_http_server, args=(8000,))
        http_server_process.start()

        # running tests
        TestBlogNotifierCLI('blog_notifier.blog_notifier').run_tests()
    finally:
        # stopping python's http.server
        # http_server_process.kill()
        if http_server_process:
            http_server_process.terminate()
            http_server_process.join()
        # removing all the html files created
        remove_fake_blog()
