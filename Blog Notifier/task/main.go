package main

import (
	"flag"
	"fmt"
	"io"
	"log"
	"net/http"
	"os"
	"sync"

	"github.com/PuerkitoBio/goquery"
	"gopkg.in/yaml.v3"
	"gorm.io/driver/sqlite"
	"gorm.io/gorm"
)

const (
	Migrate string = "migrate"
	Explore string = "explore"
	List    string = "list"
	Remove  string = "remove"

	UpdateLastLink string = "update-last-link"
	Site           string = "site"
	PostSite       string = "post"

	Crawl     string = "crawl"
	ListPosts string = "list-posts"
)

const BlogsDBPath = "blogs.sqlite3"

const MaxDepth = 3

type Config struct {
	Mode   string `yaml:"mode"`
	Server struct {
		Host string `yaml:"host"`
		Port int    `yaml:"port"`
	} `yaml:"server"`
	Client struct {
		Email    string `yaml:"email"`
		Password string `yaml:"password"`
		SendTo   string `yaml:"send_to"`
	} `yaml:"client"`
	Telegram struct {
		BotToken string `yaml:"bot_token"`
		Channel  string `yaml:"channel"`
	} `yaml:"telegram"`
}

type Blog struct {
	Site     string `gorm:"primaryKey"`
	LastLink string
}

type Post struct {
	Site string `gorm:"foreignKey:Site;constraint:OnDelete:CASCADE"`
	Link string
}

type Mail struct {
	ID     uint `gorm:"primaryKey"`
	Mail   string
	IsSent int `gorm:"default:0"`
}

type BlogNotifier struct {
	db *gorm.DB
}

func NewBlogNotifier(db *gorm.DB) *BlogNotifier {
	return &BlogNotifier{db: db}
}

func main() {
	db, err := gorm.Open(sqlite.Open(BlogsDBPath), &gorm.Config{})
	if err != nil {
		log.Fatalf("failed to open %s: %v\n", BlogsDBPath, err)
	}

	bn := NewBlogNotifier(db)

	err = bn.CliHandling()
	if err != nil {
		fmt.Printf("%v\n", err)
		return
	}
}

func (bn *BlogNotifier) CliHandling() error {
	configFile := flag.String("config", "", "Path to the YAML configuration file")

	migrateFlag := flag.Bool(Migrate, false, "Create a database with file named blogs.sqlite")
	exploreFlag := flag.String(Explore, "", "Inserts a new entry into the blogs table of the database")
	listFlag := flag.Bool(List, false, "Lists all the blog sites that are in the blogs table")
	removeFlag := flag.String(Remove, "", "Remove site from watchlist")
	crawlFlag := flag.Bool(Crawl, false, "Perform a crawl on each site in the watch list to identify new blog posts.")

	updateLastLinkFlagSet := flag.NewFlagSet(UpdateLastLink, flag.ExitOnError)
	site := updateLastLinkFlagSet.String(Site, "", "Enter the blog site")
	post := updateLastLinkFlagSet.String(PostSite, "", "Enter the post site")

	listPostFlagSet := flag.NewFlagSet(ListPosts, flag.ExitOnError)
	listPostsSiteFlag := listPostFlagSet.String(Site, "", "Take a URL of a blog-site and output all the blog-posts corresponding to that blog-site")

	flag.Parse()

	if len(os.Args) == 1 {
		return fmt.Errorf("no command input specified")
	}

	if *configFile != "" {
		data, err := os.ReadFile(*configFile)
		if err != nil {
			return fmt.Errorf("file '%s' not found", *configFile)
		}

		var config Config
		err = yaml.Unmarshal(data, &config)
		if err != nil {
			return fmt.Errorf("cannot unmarshal the config file '%s'", *configFile)
		}

		fmt.Printf("mode: %s\n", config.Mode)
		fmt.Printf("email_server: %s:%d\n", config.Server.Host, config.Server.Port)
		fmt.Printf("client: %s %s %s\n", config.Client.Email, config.Client.Password, config.Client.SendTo)
		fmt.Printf("telegram: %s@%s\n", config.Telegram.BotToken, config.Telegram.Channel)
	}

	if *migrateFlag {
		err := bn.migrate()
		if err != nil {
			return fmt.Errorf("error during migration: %w", err)
		}
		fmt.Println(" database 'blogs.sqlite3' created successfully ")
		fmt.Println(" tables 'blogs', 'posts', and 'mails' initialized ")
		return nil
	}

	if *exploreFlag != "" {
		err := bn.addNewBlogSite(*exploreFlag, *exploreFlag)
		if err != nil {
			return fmt.Errorf("error adding site to watchlist: %w", err)
		}
		fmt.Println("New blog added to watchlist:")
		fmt.Printf("site: %s\n", *exploreFlag)
		fmt.Printf("last link: %s\n", *exploreFlag)
		return nil
	}

	if *listFlag {
		blogs, err := bn.listAllBlogs()
		if err != nil {
			return fmt.Errorf("error listing sites: %w", err)
		}
		for _, blog := range blogs {
			fmt.Printf("%s %s\n", blog.Site, blog.LastLink)
		}
		return nil
	}

	if *removeFlag != "" {
		err := bn.deleteBlog(*removeFlag)
		if err != nil {
			return fmt.Errorf("error removing site from watchlist: %w", err)
		}
		fmt.Printf("%s removed from the watch list.\n", *removeFlag)
		return nil
	}

	if len(os.Args) > 1 && os.Args[1] == UpdateLastLink {
		err := updateLastLinkFlagSet.Parse(os.Args[2:])
		if err != nil {
			return fmt.Errorf("error parsing update-last-link flags: %w", err)
		}

		if *site != "" && *post != "" {
			err := bn.updateLastLinkOfBlog(*site, *post)
			if err != nil {
				return fmt.Errorf("error updating last link: %w", err)
			}
			fmt.Printf("The last link for %s updated to %s\n", *site, *post)
			return nil
		} else {
			return fmt.Errorf("for 'update-last-link' sub-command, 'site' and 'post' cannot be empty")
		}
	}

	if *crawlFlag {
		err := bn.crawlAndUpdatePosts()
		if err != nil {
			fmt.Printf("error crawling and updating posts: %s\n", err)
			return err
		}
		return nil
	}

	if len(os.Args) > 1 && os.Args[1] == ListPosts {
		err := listPostFlagSet.Parse(os.Args[2:])
		if err != nil {
			return fmt.Errorf("error parsing list-posts flags: %w", err)
		}

		if *listPostsSiteFlag != "" {
			posts, err := bn.listPostsBySite(*listPostsSiteFlag)
			if err != nil {
				return fmt.Errorf("error listing posts for site %s: %w", *listPostsSiteFlag, err)
			}
			for _, post := range posts {
				fmt.Println(post.Link)
			}
			return nil
		} else {
			return fmt.Errorf("for 'listPosts' sub-command, 'site' cannot be empty")
		}
	}

	return nil
}

func (bn *BlogNotifier) migrate() error {
	err := bn.db.AutoMigrate(&Blog{}, &Post{}, &Mail{})
	if err != nil {
		return fmt.Errorf("error creating tables: %w", err)
	}
	return nil
}

func (bn *BlogNotifier) addNewBlogSite(blogSite string, link string) error {
	var blog Blog
	result := bn.db.Where("site = ?", blogSite).First(&blog)
	if result.Error == nil {
		return fmt.Errorf("%s already exists in the watch list", blogSite)
	}

	/* Add new row to blogs table */
	blog = Blog{
		Site:     blogSite,
		LastLink: link,
	}
	result = bn.db.Create(&blog)
	if result.Error != nil {
		return fmt.Errorf("error adding site to watchlist: %w", result.Error)
	}
	return nil
}

func (bn *BlogNotifier) listAllBlogs() ([]Blog, error) {
	// Get all blogs
	var blogs []Blog
	result := bn.db.Find(&blogs)
	if result.Error != nil {
		return nil, fmt.Errorf("error fetching sites: %w", result.Error)
	}
	return blogs, nil
}

func (bn *BlogNotifier) deleteBlog(blogSite string) error {
	result := bn.db.Where("site = ?", blogSite).Delete(&Blog{})
	if result.Error != nil {
		return fmt.Errorf("error removing site from watchlist: %w", result.Error)
	}
	if result.RowsAffected == 0 {
		return fmt.Errorf("%s does not exist in the watch list", blogSite)
	}
	return nil
}

func (bn *BlogNotifier) updateLastLinkOfBlog(site string, post string) error {
	result := bn.db.Model(&Blog{}).Where("site = ?", site).Update("last_link", post)
	if result.Error != nil {
		return fmt.Errorf("error updating last link for blog %s: %w", site, result.Error)
	}
	if result.RowsAffected == 0 {
		return fmt.Errorf("%s does not exist in the watch list", site)
	}
	return nil
}

func (bn *BlogNotifier) crawlAndUpdatePosts() error {
	siteLinks, err := bn.crawlSites()
	if err != nil {
		return fmt.Errorf("error crawling blog sites: %w", err)
	}

	for site, links := range siteLinks {
		for _, link := range links {
			isNewPost, err := bn.addNewPostIfNotExist(site, link)
			if err != nil {
				return fmt.Errorf("error adding post: %w", err)
			}
			if isNewPost {
				err = bn.addMail(site, link)
				if err != nil {
					return fmt.Errorf("error creating mail: %w", err)
				}
			}
		}
		fmt.Printf("Number of new blog posts discovered for the site %s: %d\n", site, len(links))
	}

	return nil
}

func (bn *BlogNotifier) crawlSites() (map[string][]string, error) {
	blogs, err := bn.listAllBlogs()
	if err != nil {
		return nil, fmt.Errorf("error fetching blogs: %w", err)
	}

	type crawlResult struct {
		site  string
		links []string
	}

	crawlResultCh := make(chan crawlResult, len(blogs))
	errCh := make(chan error, len(blogs))
	doneCh := make(chan struct{})
	var wg sync.WaitGroup

	for _, blog := range blogs {
		wg.Add(1)
		go func(site string) {
			defer wg.Done()
			links, err := bn.crawlSite(site, site)
			if err != nil {
				errCh <- err
				return
			}
			crawlResultCh <- crawlResult{
				site:  site,
				links: links,
			}
			if len(links) > 0 {
				err = bn.updateLastVisitedSite(site, links[len(links)-1])
				if err != nil {
					errCh <- err
				}
			}
		}(blog.Site)
	}

	go func() {
		wg.Wait()
		close(crawlResultCh)
		close(errCh)
		close(doneCh)
	}()

	siteLinks := make(map[string][]string)

	for {
		select {
		case result, ok := <-crawlResultCh:
			if !ok {
				crawlResultCh = nil
			} else {
				siteLinks[result.site] = result.links
			}
		case err, ok := <-errCh:
			if !ok {
				errCh = nil
			} else {
				fmt.Println(err)
			}
		case <-doneCh:
			return siteLinks, nil
		}
	}
}

func (bn *BlogNotifier) crawlSite(site, link string) ([]string, error) {
	links, err := bn.getLinks(link)
	if err != nil {
		return nil, fmt.Errorf("%s: error getting links: %w", site, err)
	}

	var allLinks []string
	for _, link := range links {
		allLinks = append(allLinks, link)
		subLinks, err := bn.crawlSite(site, link)
		if err != nil {
			return nil, fmt.Errorf("%s: error in recursive crawl: %w", site, err)
		}
		allLinks = append(allLinks, subLinks...)
	}

	return allLinks, nil
}

func (bn *BlogNotifier) addNewPostIfNotExist(site, link string) (bool, error) {
	var post Post

	result := bn.db.Where("site = ? AND link = ?", site, link).First(&post)
	if result.Error == nil {
		return false, nil
	}

	post = Post{Site: site, Link: link}

	result = bn.db.Create(&post)
	if result.Error != nil {
		return false, fmt.Errorf("error adding post: %w", result.Error)
	}
	return true, nil
}

func (bn *BlogNotifier) addMail(site, link string) error {
	mail := Mail{Mail: fmt.Sprintf("New blog post %s on blog %s", link, site)}

	result := bn.db.Create(&mail)
	if result.Error != nil {
		return fmt.Errorf("error adding mail: %w", result.Error)
	}

	return nil
}

func (bn *BlogNotifier) getLinks(url string) ([]string, error) {
	res, err := http.Get(url)
	if err != nil {
		return nil, fmt.Errorf("could not reach the site: %s", url)
	}
	defer func(Body io.ReadCloser) {
		err := Body.Close()
		if err != nil {
			log.Printf("error closing response body: %v", err)
			return
		}
	}(res.Body)

	if res.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("unexpected status code: %d", res.StatusCode)
	}

	doc, err := goquery.NewDocumentFromReader(res.Body)
	if err != nil {
		return nil, err
	}

	var links []string
	doc.Find("a").Each(func(_ int, s *goquery.Selection) {
		link, exists := s.Attr("href")
		if exists {
			links = append(links, link)
		}
	})

	return links, nil
}

func (bn *BlogNotifier) updateLastVisitedSite(site, link string) error {
	result := bn.db.Model(&Blog{}).Where("site = ?", site).Update("last_link", link)
	if result.Error != nil {
		return fmt.Errorf("error updating last link for blog %s: %w", site, result.Error)
	}
	if result.RowsAffected == 0 {
		return fmt.Errorf("%s does not exist in the watch list", site)
	}
	return nil
}

func (bn *BlogNotifier) listPostsBySite(site string) ([]Post, error) {
	var posts []Post

	result := bn.db.Where("site = ?", site).Find(&posts)
	if result.Error != nil {
		return nil, fmt.Errorf("error fetching posts for site %s: %w", site, result.Error)
	}

	return posts, nil
}

//////////////////////////////////////////////////////////////////////////////////////////////////////////////////
//
//func crawlSite(site string) ([]string, error) {
//	links := make([]string, 0)
//	uniqueLinks := make(map[string]bool)
//
//	err := crawlSiteRecursive(site, &links, uniqueLinks, 1)
//	if err != nil {
//		return nil, err
//	}
//
//	return getUniqueLinks(links), nil
//}
//
//func crawlSiteRecursive(link string, links *[]string, uniqueLinks map[string]bool, depth int) error {
//	if depth > MaxDepth {
//		return nil
//	}
//
//	foundLinks, err := getLinks(link)
//	if err != nil {
//		return err
//	}
//
//	for _, foundLink := range foundLinks {
//		absoluteURL := resolveURL(link, foundLink)
//		if absoluteURL != "" && !uniqueLinks[absoluteURL] {
//			*links = append(*links, absoluteURL)
//			uniqueLinks[absoluteURL] = true
//			err := crawlSiteRecursive(absoluteURL, links, uniqueLinks, depth+1)
//			if err != nil {
//				return err
//			}
//		}
//	}
//	return nil
//}
//
//func resolveURL(baseURL, relativeURL string) string {
//	if relativeURL == "" {
//		return ""
//	}
//
//	parsedBaseURL, err := url.Parse(baseURL)
//	if err != nil {
//		return ""
//	}
//
//	parsedRelativeURL, err := url.Parse(relativeURL)
//	if err != nil {
//		return ""
//	}
//
//	absoluteURL := parsedBaseURL.ResolveReference(parsedRelativeURL)
//	return absoluteURL.String()
//}
//
//func getUniqueLinks(links []string) []string {
//	uniqueLinks := make([]string, 0)
//	uniqueLinksMap := make(map[string]bool)
//
//	for _, link := range links {
//		if _, ok := uniqueLinksMap[link]; !ok {
//			uniqueLinks = append(uniqueLinks, link)
//			uniqueLinksMap[link] = true
//		}
//	}
//
//	return uniqueLinks
//}
//
//func getLinks(site string) ([]string, error) {
//	res, err := http.Get(site)
//	if err != nil {
//		return nil, fmt.Errorf("could not reach the site: %s", site)
//	}
//	defer func(Body io.ReadCloser) {
//		err = Body.Close()
//		if err != nil {
//			log.Printf("could not close the response body: %v\n", err)
//			return
//		}
//	}(res.Body)
//	if res.StatusCode != http.StatusOK {
//		return nil, fmt.Errorf("unexpected status code: %d", res.StatusCode)
//	}
//
//	// Load the HTML document
//	doc, err := goquery.NewDocumentFromReader(res.Body)
//	if err != nil {
//		return nil, err
//	}
//
//	// Initialize an empty slice to store discovered links
//	links := make([]string, 0)
//
//	// Iterate over all 'a' (anchor) elements in the HTML document
//	doc.Find("a").Each(func(i int, s *goquery.Selection) {
//		// Extract the 'href' attribute value from each 'a' element
//		link, exists := s.Attr("href")
//		if exists {
//			// Add the discovered link to the slice
//			links = append(links, link)
//		}
//	})
//	return links, nil
//}
