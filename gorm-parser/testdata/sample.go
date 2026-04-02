package main

import "gorm.io/gorm"

func test(db *gorm.DB) {
	var result interface{}

	db.Where("account_id = ?", "16").First(&result)
	db.Where("name = ?", "abc").Where("status = ?", "active").Find(&result)
}