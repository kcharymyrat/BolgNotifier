import multiprocessing

from test.blognotifier_test_utils import *
from test.tests import TestBlogNotifierCLI


if __name__ == '__main__':
    http_server_process: multiprocessing.Process = None
    smtp_server_process: multiprocessing.Process = None
    mail_queue: Queue = Queue()  # aiosmtpd server will put mails it receives from the program in this queue
    stop_server_signal_queue: Queue = Queue()  # is used to send signal when to stop aiosmtpd server
    try:
        # creating fake blog(just html files) for testing
        create_blog_site_with_no_posts()
        create_blog_site_with_nested_posts(1, NESTED_LINKS_TEST_1)
        create_blog_site_with_nested_posts(2, NESTED_LINKS_TEST_2)
        create_blog_site_with_nested_posts(3, NESTED_LINKS_TEST_3)
        create_flat_blog_site_with_multiple_posts()
        create_blog_site_with_nested_and_flat_posts()

        # starting python's http.server
        http_server_process = multiprocessing.Process(target=run_http_server, args=(8000,))
        http_server_process.start()

        # starting aiosmtpd.server
        smtp_server_process = multiprocessing.Process(target=start_smtp_server, args=(mail_queue, stop_server_signal_queue))
        smtp_server_process.start()
        # getting aiosmtpd server's address
        controller_info = {}
        controller_info['hostname'] = mail_queue.get()
        controller_info['port'] = mail_queue.get()
        print(f'successfully received config of smtp server {controller_info}')
        # config_map['server']['host'] = mail_queue.get()
        # config_map['server']['port'] = mail_queue.get()

        # running tests
        TestBlogNotifierCLI(mail_queue, stop_server_signal_queue).run_tests()
    finally:
        # time.sleep(60)
        print('stopping the http server')
        # stopping python's http.server
        # http_server_process.kill()
        if http_server_process:
            http_server_process.terminate()
            http_server_process.join()
        print('successfully stopped http server')

        # removing all the html files created
        print('removing the html files generated for testcases')
        remove_fake_blog()
        print('successfully removed the html files generated for test cases')

        # stopping SMTP server
        print('stopping the smtp server')
        stop_server_signal_queue.put(None)
        mail_queue.close()
        stop_server_signal_queue.close()
        smtp_server_process.kill()
        print('successfully stopped smtp server')
