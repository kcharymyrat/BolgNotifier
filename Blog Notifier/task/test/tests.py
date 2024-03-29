import multiprocessing, yaml
from .blognotifier_test_utils import *

from hstest import StageTest, TestedProgram, CheckResult, dynamic_test


class TestBlogNotifierCLI(StageTest):
    def __init__(self, *args, **kwargs):
        super().__init__()
        for arg in args:
            print(arg)
        for k, v in kwargs.items():
            print(f"{k}: {v}")
        self.mail_queue = args[0]  # kwargs['mail_queue']
        self.stop_server_signal_queue = args[1]  # kwargs['stop_server_signal_queue']

    @dynamic_test(time_limit=120000)
    def test1_migrate_command(self):
        # Test the --migrate sub-command which creates the blogs.sqlite3 database and tables
        remove_db_file()
        program = TestedProgram()
        program.start("--migrate").strip().lower()

        for table_name in tables_properties:
            if check_table_exists(table_name) is False:
                raise CheckResult.wrong(f"The --migrate command did not create the '{table_name}' table.")
            temp = check_table_properties(table_name)
            if temp[0] is False:
                raise CheckResult.wrong(
                    f"Wrong column types for '{table_name}' table. Expected column types for the '{table_name}' table are {tables_properties[table_name]}. Found {temp[1]}")

        return CheckResult.correct()

    @dynamic_test(time_limit=120000)
    def test2_crawling_with_no_hyperlinks(self):
        # Test the crawl flag and list-posts sub-command.
        remove_db_file()
        program = TestedProgram()
        program.start("--migrate")
        program = TestedProgram()
        blog = blog_files[NO_LINKS_TEST]
        program.start('--explore', blog)
        program = TestedProgram()
        program.start("sync", "--conf", "credentials.yaml")

        program = TestedProgram()
        output = program.start("list-posts", "--site", blog_files[NO_LINKS_TEST])

        output.strip()

        # Expected links from the example output
        expected_output = ""

        # Check if all expected links are present in the output
        if expected_output != output:
            return CheckResult.wrong(
                f"The output of the program does not match the expected output for the list-posts sub-command."
                f"\nYour program output: {output}"
                f"\nExpected output: {expected_output}")

        program = TestedProgram()
        output = program.start("--list")

        output.strip()

        if f'{blog} {blog}' not in output:
            return CheckResult.wrong("list flag returned wrong output. 'last_link' cloumn in the blogs table must be "
                                     "only updated when new blog-post for that blog site are found")

        return CheckResult.correct()

    @dynamic_test(time_limit=120000)
    def test3_crawling_with_nested_links_a(self):
        # Test the crawl flag and list-posts sub-command for blog with one blog-posts.
        # prepping for tests
        remove_db_file()
        program = TestedProgram()
        program.start("--migrate")
        program = TestedProgram()
        blog = blog_files[NESTED_LINKS_TEST_1][-1]
        program.start('--explore', blog)
        config_map['client']['email'] = f'{generate_random_text(6)}.{random.choice(["com", "net"])}'
        config_map['client']['password'] = generate_random_text(10)
        config_map['client']['send_to'] = f'{generate_random_text(6)}.{random.choice(["com", "net"])}'
        yaml_content = yaml.dump(config_map)
        create_yaml_file('credentials.yaml', yaml_content)

        # testing sync command
        program = TestedProgram()
        program.start("sync", "--conf", "credentials.yaml")

        # checking if the mails were actually sent
        expected_msgs = [
            f'New blog-post {blog_files[NESTED_LINKS_TEST_1][0]} on blog {blog_files[NESTED_LINKS_TEST_1][-1]}']
        for i in range(len(expected_msgs)):
            msg = self.mail_queue.get()
            if msg.get('from', "") != config_map['client']['email']:
                return CheckResult.wrong(
                    f"Test was carried out for the sync sub-command, seems that sending emails is not correctly "
                    f"implemented. expected sender_email: {config_map['client']['email']}, got sender_email: "
                    f"{msg.get('from', '')}")
            if msg.get('to', "") != config_map['client']['send_to']:
                return CheckResult.wrong(
                    f"Test was carried out for the sync sub-command, seems that sending emails is not correctly "
                    f"implemented. expected receiver_email: {config_map['client']['send_to']}, got receiver_email: "
                    f"{msg.get('to', '')}")
            if expected_msgs[0] not in msg.get('message', ""):
                return CheckResult.wrong(
                    f"Test was carried out for the sync sub-command, seems that sending emails is not correctly "
                    f"implemented. expected message: {expected_msgs[0]}, output message: {msg.get('message', '')}")

        # testing if the posts table in the database was updated with correct values
        program = TestedProgram()
        output = program.start("list-posts", "--site", blog)
        output.strip()
        # Expected links from the example output
        expected_output = blog_files[NESTED_LINKS_TEST_1][0]
        # Check if all expected links are present in the output
        if expected_output not in output:
            return CheckResult.wrong(
                f"Test was carried out for blog site with just one blog post expected_output: {expected_output} program_output: {output}")

        # testing if the last_link column in the blogs table was updated
        program = TestedProgram()
        output = program.start("--list")
        output.strip()
        if f'{blog} {expected_output}' in output:
            return CheckResult.correct()
        return CheckResult.wrong(
            f"Test was carried out for blog site with just one hyperlink, seams like the last_link column in the blogs "
            f"table is not updated after crawling")

    @dynamic_test(time_limit=120000)
    def test4_crawling_with_nested_links_b(self):
        # Test the crawl flag and list-posts sub-command for blog with 2 nested blog-posts.
        # prepping for the test
        remove_db_file()
        program = TestedProgram()
        program.start("--migrate")
        program = TestedProgram()
        blog = blog_files[NESTED_LINKS_TEST_2][-1]
        program.start('--explore', blog)
        config_map['client']['email'] = f'{generate_random_text(6)}.{random.choice(["com", "net"])}'
        config_map['client']['password'] = generate_random_text(10)
        config_map['client']['send_to'] = f'{generate_random_text(6)}.{random.choice(["com", "net"])}'
        yaml_content = yaml.dump(config_map)
        create_yaml_file('credentials.yaml', yaml_content)

        # testing sync command
        program = TestedProgram()
        program.start("sync", "--conf", "credentials.yaml")

        # testing if the mails were actually sent
        expected_msgs = [f'New blog-post {blog_post} on blog {blog_files[NESTED_LINKS_TEST_2][-1]}' for blog_post in
                         blog_files[NESTED_LINKS_TEST_2][:-1]]
        for i in range(len(expected_msgs)):
            msg = self.mail_queue.get()
            if msg.get('from', "") != config_map['client']['email']:
                return CheckResult.wrong(
                    f"Test was carried out for the sync sub-command, seems that sending emails is not correctly "
                    f"implemented. expected sender_email: {config_map['client']['email']}, got sender_email: "
                    f"{msg.get('from', '')}")
            if msg.get('to', "") != config_map['client']['send_to']:
                return CheckResult.wrong(
                    f"Test was carried out for the sync sub-command, seems that sending emails is not correctly "
                    f"implemented. expected receiver_email: {config_map['client']['send_to']}, got receiver_email: "
                    f"{msg.get('to', '')}")
            found = False
            e_msg = ""
            for expected_msg in expected_msgs:
                e_msg = expected_msg
                if expected_msg in msg.get('message', ""):
                    found = True
                    break
            if not found:
                CheckResult.wrong(
                    f"Test was carried out for the sync sub-command, seems that sending emails is not correctly "
                    f"implemented. expected message: {e_msg}")

        # testing if the posts table in the database was updated with correct values
        program = TestedProgram()
        output = program.start("list-posts", "--site", blog)
        output.strip()
        # Expected links from the example output
        expected_output = blog_files[NESTED_LINKS_TEST_2][:-1]
        # Check if all expected links are present in the output
        for link in expected_output:
            if link not in output:
                return CheckResult.wrong(f"Test was carried out for blog site with two blog posts {link} not found in "
                                         f"the program output")

        # testing if the last_link column in the blogs table was updated
        program = TestedProgram()
        output = program.start("--list")
        output.strip()
        for link in expected_output:
            if f'{blog} {link}' in output:
                return CheckResult.correct()
        return CheckResult.wrong(
            f"Test was carried out for blog site with two nested blog posts seems like the last_link column in the "
            f"blogs"
            f"table is not updated after crawling")

    @dynamic_test(time_limit=120000)
    def test5_crawling_with_nested_links_c(self):
        # Test the crawl flag and list-posts sub-command for blog with 3 nested blog-posts.
        # prepping for the test
        remove_db_file()
        program = TestedProgram()
        program.start("--migrate")
        program = TestedProgram()
        blog = blog_files[NESTED_LINKS_TEST_3][-1]
        program.start('--explore', blog)
        config_map['client']['email'] = f'{generate_random_text(6)}.{random.choice(["com", "net"])}'
        config_map['client']['password'] = generate_random_text(10)
        config_map['client']['send_to'] = f'{generate_random_text(6)}.{random.choice(["com", "net"])}'
        yaml_content = yaml.dump(config_map)
        create_yaml_file('credentials.yaml', yaml_content)

        # testing sync command
        program = TestedProgram()
        program.start("sync", "--conf", "credentials.yaml")

        # testing if the mails were actually sent
        expected_msgs = [f'New blog-post {blog_post} on blog {blog_files[NESTED_LINKS_TEST_3][-1]}' for blog_post in
                         blog_files[NESTED_LINKS_TEST_3][:-1]]
        for i in range(len(expected_msgs)):
            msg = self.mail_queue.get()
            if msg.get('from', "") != config_map['client']['email']:
                return CheckResult.wrong(
                    f"Test was carried out for the sync sub-command, seems that sending emails is not correctly "
                    f"implemented. expected sender_email: {config_map['client']['email']}, got sender_email: "
                    f"{msg.get('from', '')}")
            if msg.get('to', "") != config_map['client']['send_to']:
                return CheckResult.wrong(
                    f"Test was carried out for the sync sub-command, seems that sending emails is not correctly "
                    f"implemented. expected receiver_email: {config_map['client']['send_to']}, got receiver_email: "
                    f"{msg.get('to', '')}")
            found = False
            e_msg = ""
            for expected_msg in expected_msgs:
                e_msg = expected_msg
                if expected_msg in msg.get('message', ""):
                    found = True
                    break
            if not found:
                CheckResult.wrong(
                    f"Test was carried out for the sync sub-command, seems that sending emails is not correctly "
                    f"implemented. expected message: {e_msg}")

        # testing if the posts table in the database was updated with correct values
        program = TestedProgram()
        output = program.start("list-posts", "--site", blog)
        output.strip()
        # Expected links from the example output
        expected_output = blog_files[NESTED_LINKS_TEST_3][:-1]
        # Check if all expected links are present in the output
        for link in expected_output:
            if link not in output:
                return CheckResult.wrong(
                    f"Test was carried out for blog site with three nested blog posts {link} not found in "
                    f"the program output")

        # testing if the last_link column in the blogs table was updated
        program = TestedProgram()
        output = program.start("--list")
        output.strip()
        for link in expected_output:
            if f'{blog} {link}' in output:
                return CheckResult.correct()
        return CheckResult.wrong(
            f"Test was carried out for blog site with three nested blog posts, seems like the last_link column in the "
            f"blogs table is not updated after crawling")

    @dynamic_test(time_limit=120000)
    def test6_crawling_with_flat_multiple_pages(self):
        # Test the crawl flag and list-posts sub-command for blog with many blog-posts.
        # prepping for the test
        remove_db_file()
        program = TestedProgram()
        program.start("--migrate")
        program = TestedProgram()
        blog = blog_files[FLAT_MULTIPLE_LINKS_TEST][-1]
        program.start('--explore', blog)
        config_map['client']['email'] = f'{generate_random_text(6)}.{random.choice(["com", "net"])}'
        config_map['client']['password'] = generate_random_text(10)
        config_map['client']['send_to'] = f'{generate_random_text(6)}.{random.choice(["com", "net"])}'
        yaml_content = yaml.dump(config_map)
        create_yaml_file('credentials.yaml', yaml_content)

        # testing sync command
        program = TestedProgram()
        program.start("sync", "--conf", "credentials.yaml")

        # testing if the mails were actually sent
        expected_msgs = [f'New blog-post {blog_post} on blog {blog_files[FLAT_MULTIPLE_LINKS_TEST][-1]}' for blog_post
                         in blog_files[FLAT_MULTIPLE_LINKS_TEST][:-1]]
        for i in range(len(expected_msgs)):
            msg = self.mail_queue.get()
            if msg.get('from', "") != config_map['client']['email']:
                return CheckResult.wrong(
                    f"Test was carried out for the sync sub-command, seems that sending emails is not correctly "
                    f"implemented. expected sender_email: {config_map['client']['email']}, got sender_email: "
                    f"{msg.get('from', '')}")
            if msg.get('to', "") != config_map['client']['send_to']:
                return CheckResult.wrong(
                    f"Test was carried out for the sync sub-command, seems that sending emails is not correctly "
                    f"implemented. expected receiver_email: {config_map['client']['send_to']}, got receiver_email: "
                    f"{msg.get('to', '')}")
            found = False
            e_msg = ""
            for expected_msg in expected_msgs:
                e_msg = expected_msg
                if expected_msg in msg.get('message', ""):
                    found = True
                    break
            if not found:
                CheckResult.wrong(
                    f"Test was carried out for the sync sub-command, seems that sending emails is not correctly "
                    f"implemented. expected message: {e_msg}")

        # testing if the posts table in the database was updated with correct values
        program = TestedProgram()
        output = program.start("list-posts", "--site", blog)
        output.strip()
        # Expected links from the example output
        expected_output = blog_files[FLAT_MULTIPLE_LINKS_TEST][:-1]
        # Check if all expected links are present in the output
        for link in expected_output:
            if link not in output:
                return CheckResult.wrong(
                    f"Test was carried out for blog site with multiple blog posts {link} not found in "
                    f"the program output")

        # testing if the last_link column in the blogs table was updated
        program = TestedProgram()
        output = program.start("--list")
        output.strip()
        for link in expected_output:
            if f'{blog} {link}' in output:
                return CheckResult.correct()
        return CheckResult.wrong(
            f"Test was carried out for blog site with multiple blog posts seems like the last_link column in the blogs "
            f"table is not updated after crawling")

    @dynamic_test(time_limit=120000)
    def test7_crawling_with_nested_and_flat_posts(self):
        # Test the crawl flag and list-posts sub-command for blog with many blog-posts (flat and nested).
        # prepping for the test
        remove_db_file()
        program = TestedProgram()
        program.start("--migrate")
        program = TestedProgram()
        blog = blog_files[NESTED_AND_FLAT_LINKS_TEST][-1]
        program.start('--explore', blog)
        config_map['client']['email'] = f'{generate_random_text(6)}.{random.choice(["com", "net"])}'
        config_map['client']['password'] = generate_random_text(10)
        config_map['client']['send_to'] = f'{generate_random_text(6)}.{random.choice(["com", "net"])}'
        yaml_content = yaml.dump(config_map)
        create_yaml_file('credentials.yaml', yaml_content)

        # testing sync command
        program = TestedProgram()
        program.start("sync", "--conf", "credentials.yaml")

        # testing if the mails were actually sent
        expected_msgs = [f'New blog-post {blog_post} on blog {blog_files[NESTED_AND_FLAT_LINKS_TEST][-1]}' for blog_post
                         in blog_files[NESTED_AND_FLAT_LINKS_TEST][:-1]]
        for i in range(len(expected_msgs)):
            msg = self.mail_queue.get()
            if msg.get('from', "") != config_map['client']['email']:
                return CheckResult.wrong(
                    f"Test was carried out for the sync sub-command, seems that sending emails is not correctly "
                    f"implemented. expected sender_email: {config_map['client']['email']}, got sender_email: "
                    f"{msg.get('from', '')}")
            if msg.get('to', "") != config_map['client']['send_to']:
                return CheckResult.wrong(
                    f"Test was carried out for the sync sub-command, seems that sending emails is not correctly "
                    f"implemented. expected receiver_email: {config_map['client']['send_to']}, got receiver_email: "
                    f"{msg.get('to', '')}")
            found = False
            e_msg = ""
            for expected_msg in expected_msgs:
                e_msg = expected_msg
                if expected_msg in msg.get('message', ""):
                    found = True
                    break
            if not found:
                CheckResult.wrong(
                    f"Test was carried out for the sync sub-command, seems that sending emails is not correctly "
                    f"implemented. expected message: {e_msg}")

        # testing if the posts table in the database was updated with correct values
        program = TestedProgram()
        output = program.start("list-posts", "--site", blog)
        # Expected links from the example output
        expected_links = blog_files[NESTED_AND_FLAT_LINKS_TEST][:-1]
        # Check if all expected links are present in the output
        for link in expected_links:
            if link not in output:
                return CheckResult.wrong(
                    f"Test was carried out for blog site with multiple blog posts flat and nested. {link} not found in "
                    f"the program output")

        # testing if the last_link column in the blogs table was updated
        program = TestedProgram()
        output = program.start("--list")
        output.strip()
        for link in expected_links:
            if f'{blog} {link}' in output:
                return CheckResult.correct()

        return CheckResult.wrong(
            f"Test was carried out for blog site with multiple flat and nested blog posts seems like the last_link "
            f"column in the blogs table is not updated after crawling")


if __name__ == '__main__':
    TestBlogNotifierCLI().run_tests()
