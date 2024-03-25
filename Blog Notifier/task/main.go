package main

import (
	"errors"
	"flag"
	"fmt"
	"github.com/PuerkitoBio/goquery"
	"gorm.io/driver/sqlite"
	"gorm.io/gorm"
	"io"
	"log"
	"net/http"
	"net/url"
	"os"
)

const (
	Migrate   string = "migrate"
	Explore   string = "explore"
	List      string = "list"
	Remove    string = "remove"
	CrawlSite string = "crawl-site"

	UpdateLastLink string = "update-last-link"
	Site           string = "site"
	PostSite       string = "post"
)

const (
	BlogsDBPath = "./blogs.sqlite3"
)

const MaxDepth = 3

// Blog represents the blogs table in the database
type Blog struct {
	Site     string `gorm:"primaryKey"`
	LastLink string
}

// Post represents the posts table in the database
type Post struct {
	Site string `gorm:"foreignKey:Site;constraint:OnDelete:CASCADE"`
	Link string
}

// Mail represents the mails table in the database
type Mail struct {
	ID     uint `gorm:"primaryKey"`
	Mail   string
	IsSent int `gorm:"default:0"`
}

func main() {
	_, err := CliHandling()
	if err != nil {
		return
	}
}

func CliHandling() (*gorm.DB, error) {
	migrateFlag := flag.Bool(Migrate, false, "Create a database with file named blogs.sqlite")
	exploreFlag := flag.String(Explore, "", "Inserts a new entry into the blogs table of the database")
	listFlag := flag.Bool(List, false, "Lists all the blog sites that are in the blogs table")
	removeFlag := flag.String(Remove, "", "")
	crawlFlag := flag.String(CrawlSite, "", "")

	// Declare new subcommand
	updateLastLinkFlagSet := flag.NewFlagSet(UpdateLastLink, flag.ExitOnError)
	// declare commands on updateLastLinkFlagSet
	site := updateLastLinkFlagSet.String(Site, "", "Enter the blog site")
	post := updateLastLinkFlagSet.String(PostSite, "", "Enter the post site")

	if len(os.Args) < 2 {
		fmt.Println("no command input specified")
		flag.Usage()
		return nil, errors.New("no command input specified")
	}

	if len(os.Args) <= 3 {
		flag.Parse()

		if *migrateFlag {
			db, err := migrate()
			if err != nil {
				return nil, err
			}
			fmt.Println(" database 'blogs.sqlite3' created successfully ")
			fmt.Println(" tables 'blogs', 'posts', and 'mails' initialized ")
			return db, err
		}

		if *exploreFlag != "" {
			db, err := explore(*exploreFlag)
			if err != nil {
				return nil, err
			}

			return db, err
		}

		if *listFlag {
			db, err := listAllBlogs()
			if err != nil {
				return nil, err
			}
			return db, err
		}

		if *removeFlag != "" {
			db, err := deleteBlog(*removeFlag)
			if err != nil {
				return nil, err
			}
			return db, err
		}

		if *crawlFlag != "" {
			links, err := crawlSite(*crawlFlag)
			if err != nil {
				fmt.Printf("could not reach the site: %s\n", *crawlFlag)
				return nil, err
			}
			if len(links) == 0 {
				fmt.Printf("No blog posts found for %s\n", *crawlFlag)
				return nil, nil
			}
			for _, link := range links {
				fmt.Println(link)
			}
			return nil, nil
		}
	} else if os.Args[1] == UpdateLastLink {
		err := updateLastLinkFlagSet.Parse(os.Args[2:])
		if err != nil {
			return nil, err
		}

		if *site != "" && *post != "" {
			db, err := updateBlog(*site, *post)
			if err != nil {
				return nil, err
			}
			fmt.Printf("The last link for %s updated to %s\n", *site, *post)
			return db, err
		} else {
			fmt.Println("For 'update-last-link' sub-command, 'site' and 'post' cannot be empty")
			return nil, errors.New("'site' and 'post' cannot be empty")
		}
	}

	fmt.Println("Invalid command")
	return nil, errors.New("invalid command")
}

func dbConnection() (*gorm.DB, error) {
	// connect to SQLite db
	db, err := gorm.Open(sqlite.Open(BlogsDBPath), &gorm.Config{})
	if err != nil {
		return nil, err
	}

	// Auto-migrate the schema
	err = db.AutoMigrate(&Blog{}, &Post{}, &Mail{})
	if err != nil {
		return nil, err
	}

	return db, nil
}

func migrate() (*gorm.DB, error) {
	return dbConnection()
}

func explore(blogSite string) (*gorm.DB, error) {
	// Connect to db
	db, err := dbConnection()
	if err != nil {
		return nil, err
	}

	/* Add new row to blogs table */
	blog := Blog{
		Site:     blogSite,
		LastLink: blogSite,
	}

	result := db.Create(&blog)
	if result.Error != nil {
		fmt.Printf(" %v already exists in the watch list \n", blogSite)
		return nil, result.Error
	}

	fmt.Println(" New blog added to watchlist ")
	fmt.Printf(" site: %s \n", blogSite)
	fmt.Printf(" last link: %s \n", blogSite)

	return db, nil
}

func listAllBlogs() (*gorm.DB, error) {
	// Connect to db
	db, err := dbConnection()
	if err != nil {
		return nil, err
	}

	// Get all blogs
	var blogs []Blog
	result := db.Find(&blogs)
	if result.Error != nil {
		log.Fatalf("cannot retrieve Blogs: %v\n", result.Error)
		return nil, result.Error
	}

	// Print blogs
	for _, blog := range blogs {
		fmt.Printf("%s %s\n", blog.Site, blog.LastLink)
	}

	return db, nil
}

func deleteBlog(blogSite string) (*gorm.DB, error) {
	// Connect to db
	db, err := dbConnection()
	if err != nil {
		return nil, err
	}

	// Retrieve blog
	var blog Blog
	result := db.Where("Site = ?", blogSite).First(&blog)
	if result.Error != nil {
		fmt.Printf(" %v does not exist in the watch list \n", blogSite)
		return nil, result.Error
	}

	// Delete the blog
	result = db.Delete(&blog)
	if result.Error != nil {
		return nil, result.Error
	}

	fmt.Printf(" %v removed from the watch list. \n", blogSite)
	return db, nil
}

func updateBlog(site string, post string) (*gorm.DB, error) {
	// Connect to db
	db, err := dbConnection()
	if err != nil {
		return nil, err
	}

	// Retrieve blog
	var blog Blog
	result := db.Where("Site = ?", site).First(&blog)
	if result.Error != nil {
		fmt.Printf("%s does not exist in the watch list\n", site)
		return nil, result.Error
	}

	blog.LastLink = post

	result = db.Save(&blog)
	if result.Error != nil {
		log.Fatalf("cannot update Blog: %v\n", result.Error)
		return nil, result.Error
	}

	return db, nil
}

func crawlSite(site string) ([]string, error) {
	links := make([]string, 0)
	uniqueLinks := make(map[string]bool)

	err := crawlRecursive(site, &links, uniqueLinks, 1)
	if err != nil {
		return nil, err
	}

	return getUniqueLinks(links), nil
}

func crawlRecursive(link string, links *[]string, uniqueLinks map[string]bool, depth int) error {
	if depth > MaxDepth {
		return nil
	}

	foundLinks, err := getLinks(link)
	if err != nil {
		return err
	}

	for _, foundLink := range foundLinks {
		absoluteURL := resolveURL(link, foundLink)
		if absoluteURL != "" && !uniqueLinks[absoluteURL] {
			*links = append(*links, absoluteURL)
			uniqueLinks[absoluteURL] = true
			err := crawlRecursive(absoluteURL, links, uniqueLinks, depth+1)
			if err != nil {
				return err
			}
		}
	}
	return nil
}

func getLinks(site string) ([]string, error) {
	res, err := http.Get(site)
	if err != nil {
		return nil, fmt.Errorf("could not reach the site: %s", site)
	}
	defer func(Body io.ReadCloser) {
		err = Body.Close()
		if err != nil {
			log.Printf("could not close the response body: %v\n", err)
			return
		}
	}(res.Body)
	if res.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("unexpected status code: %d", res.StatusCode)
	}

	// Load the HTML document
	doc, err := goquery.NewDocumentFromReader(res.Body)
	if err != nil {
		return nil, err
	}

	// Initialize an empty slice to store discovered links
	links := make([]string, 0)

	// Iterate over all 'a' (anchor) elements in the HTML document
	doc.Find("a").Each(func(i int, s *goquery.Selection) {
		// Extract the 'href' attribute value from each 'a' element
		link, exists := s.Attr("href")
		if exists {
			// Add the discovered link to the slice
			links = append(links, link)
		}
	})
	return links, nil
}

func resolveURL(baseURL, relativeURL string) string {
	if relativeURL == "" {
		return ""
	}

	parsedBaseURL, err := url.Parse(baseURL)
	if err != nil {
		return ""
	}

	parsedRelativeURL, err := url.Parse(relativeURL)
	if err != nil {
		return ""
	}

	absoluteURL := parsedBaseURL.ResolveReference(parsedRelativeURL)
	return absoluteURL.String()
}

func getUniqueLinks(links []string) []string {
	uniqueLinks := make([]string, 0)
	uniqueLinksMap := make(map[string]bool)

	for _, link := range links {
		if _, ok := uniqueLinksMap[link]; !ok {
			uniqueLinks = append(uniqueLinks, link)
			uniqueLinksMap[link] = true
		}
	}

	return uniqueLinks
}
