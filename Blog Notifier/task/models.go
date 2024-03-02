package main

//type Blog struct {
//	Site     string `gorm:"primaryKey"`
//	LastLink string
//	Posts    []Post `gorm:"constraint:OnDelete:CASCADE"`
//}
//
//type Post struct {
//	ID   uint `gorm:"primaryKey"`
//	Site string
//	Link string
//	Blog Blog `gorm:"foreignKey:Site;references:Site"`
//}
//
//type Mail struct {
//	ID     uint   `gorm:"primaryKey;autoIncrement"`
//	Mail   string `gorm:"unique;not null"`
//	IsSent uint   `gorm:"default:0"`
//}
//
//func dbConnection() (*gorm.DB, error) {
//	// connect to SQLite db
//	db, err := gorm.Open(sqlite.Open(BLOGS_DB_PATH), &gorm.Config{})
//	if err != nil {
//		return nil, nil
//	}
//
//	// Auto-migrate the schema
//	err = db.AutoMigrate(&Blog{}, &Post{}, &Mail{})
//	if err != nil {
//		return nil, nil
//	}
//
//	// Set up foreign key constraint
//	if err := db.Migrator().CreateConstraint(&Post{}, "Blog"); err != nil {
//		return nil, err
//	}
//
//	return db, nil
//}
//
//func migrate() (*gorm.DB, error) {
//	return dbConnection()
//}
//
//func explore(blogSite string) (*gorm.DB, error) {
//	// Connect to db
//	db, err := dbConnection()
//	if err != nil {
//		return nil, err
//	}
//
//	/* Add new row to blogs table */
//	var blog Blog = Blog{
//		Site:     blogSite,
//		LastLink: blogSite,
//	}
//
//	result := db.Create(&blog)
//	if result.Error != nil {
//		log.Fatalf("cannot create Blog: %v\n", result.Error)
//		return nil, result.Error
//	}
//	return db, nil
//}
//
//func listAllBlogs() (*gorm.DB, error) {
//	// Connect to db
//	db, err := dbConnection()
//	if err != nil {
//		return nil, err
//	}
//
//	// Get all blogs
//	var blogs []Blog
//	result := db.Find(&blogs)
//	if result.Error != nil {
//		log.Fatalf("cannot retrieve Blogs: %v\n", result.Error)
//		return nil, result.Error
//	}
//
//	// Print blogs
//	for _, blog := range blogs {
//		fmt.Printf("%s %s\n", blog.Site, blog.LastLink)
//	}
//
//	return db, nil
//}
//
//func deleteBlog(blogSite string) (*gorm.DB, error) {
//	// Connect to db
//	db, err := dbConnection()
//	if err != nil {
//		return nil, err
//	}
//
//	// Retrieve blog
//	var blog Blog
//	result := db.Where("Site = ?", blogSite).First(&blog)
//	if result.Error != nil {
//		log.Fatalf("cannot retrieve Publisher: %v\n", result.Error)
//		return nil, err
//	}
//
//	// Soft delete
//	result = db.Delete(&blog)
//	if result.Error != nil {
//		log.Fatalf("cannot delete Publisher: %v\n", result.Error)
//		return nil, err
//	}
//
//	//fmt.Printf("Rows deleted: %d\n", result.RowsAffected)
//	return db, nil
//}
//
//func updateBlog(site string, post string) (*gorm.DB, error) {
//	// Connect to db
//	db, err := dbConnection()
//	if err != nil {
//		return nil, err
//	}
//
//	// Retrieve blog
//	var blog Blog
//	result := db.Where("Site = ?", site).First(&blog)
//	if result.Error != nil {
//		log.Fatalf("cannot retrieve Publisher: %v\n", result.Error)
//		return nil, err
//	}
//
//	blog.LastLink = post
//
//	result = db.Debug().Save(&blog)
//	if result.Error != nil {
//		log.Fatalf("cannot update Author: %v\n", result.Error)
//		return nil, err
//	}
//
//	return db, nil
//}
