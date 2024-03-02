package main

import (
	"errors"
	"flag"
	"fmt"
	"gorm.io/driver/sqlite"
	"gorm.io/gorm"
	"log"
	"os"
)

const (
	MIGRATE string = "migrate"
	EXPLORE string = "explore"
	LIST    string = "list"
	REMOVE  string = "remove"

	UPDATE_LAST_LINK string = "update-last-link"
	SITE             string = "site"
	POST             string = "post"
)

const (
	BLOGS_DB_PATH = "./blogs.sqlite3"
)

type Blog struct {
	Site     string `gorm:"type:TEXT;primaryKey"`
	LastLink string `gorm:"type:TEXT"`
	Posts    []Post `gorm:"foreignKey:Site;references:Site;constraint:OnUpdate:CASCADE,OnDelete:CASCADE;"`
}

type Post struct {
	Link string `gorm:"type:TEXT;primaryKey"`
	Site string `gorm:"type:TEXT"`
}

type Mail struct {
	ID     uint   `gorm:"type:INTEGER;primaryKey;autoIncrement"`
	Mail   string `gorm:"type:TEXT"`
	IsSent uint   `gorm:"type:INTEGER;default:0"`
}

func main() {
	_, err := CliHandling()
	if err != nil {
		return
	}
}

func CliHandling() (*gorm.DB, error) {

	migrateFlag := flag.Bool(MIGRATE, false, "Create a database with file named blogs.sqlite")
	exploreFlag := flag.String(EXPLORE, "", "Inserts a new entry into the blogs table of the database")
	listFlag := flag.Bool(LIST, false, "Lists all the blog sites that are in the blogs table")
	removeFlag := flag.String(REMOVE, "", "")

	// Declare new subcommand
	updateLastLinkFlagSet := flag.NewFlagSet(UPDATE_LAST_LINK, flag.ExitOnError)
	// declare commands on updateLastLinkFlagSet
	site := updateLastLinkFlagSet.String(SITE, "", "Enter the blog site")
	post := updateLastLinkFlagSet.String(POST, "", "Enter the post site")

	//fmt.Printf("os.Args = %v\n", os.Args)

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
	} else if os.Args[1] == UPDATE_LAST_LINK {
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
			return nil, err
		}
	}

	fmt.Println("Invalid command")
	return nil, errors.New("something wrong happened")
}

func dbConnection() (*gorm.DB, error) {
	// connect to SQLite db
	db, err := gorm.Open(sqlite.Open(BLOGS_DB_PATH), &gorm.Config{})
	if err != nil {
		return nil, nil
	}

	// Auto-migrate the schema
	err = db.AutoMigrate(&Blog{}, &Post{}, &Mail{})
	if err != nil {
		return nil, nil
	}

	// Set up foreign key constraint
	if err := db.Migrator().CreateConstraint(&Post{}, "Blog"); err != nil {
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
		Posts:    []Post{},
	}

	result := db.Create(&blog)
	if result.Error != nil {
		fmt.Printf(" %v already exists in the watch list \n", blogSite)
		return nil, result.Error
	}

	fmt.Println(" New blog added to watchlist ")
	fmt.Printf(" site: %s \n", blogSite)
	fmt.Printf(" last link: %s \n", blogSite)
	// "site: https://hyperskill.org/blog/" not in output
	//or "last link: https://hyperskill.org/blog/"

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
		return nil, err
	}

	// Soft delete
	result = db.Delete(&blog)
	if result.Error != nil {
		return nil, err
	}

	// https://blog1.com removed from the watch list.
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
		log.Fatalf("cannot retrieve Publisher: %v\n", result.Error)
		return nil, err
	}

	blog.LastLink = post

	result = db.Debug().Save(&blog)
	if result.Error != nil {
		log.Fatalf("cannot update Author: %v\n", result.Error)
		return nil, err
	}

	return db, nil
}
