package main

import "gorm.io/gorm"

func fetchOrdersN1(db *gorm.DB, ids []int) {
    var orders []Order

    // N+1 pattern: Where("id = ?").First() inside a loop
    for _, id := range ids {
        var order Order
        db.Where("id = ?", id).First(&order)
        orders = append(orders, order)
    }
}

func fetchWithoutPreload(db *gorm.DB) {
    var users []User

    // Missing Preload inside loop
    for i := 0; i < 10; i++ {
        var user User
        db.Find(&user)
        users = append(users, user)
    }
}

func longTransaction(db *gorm.DB) {
    // Long-held transaction
    tx := db.Begin()
    tx.Where("id = ?", 1).First(&User{})
    tx.Where("id = ?", 2).First(&Order{})
    tx.Where("id = ?", 3).First(&Order{})
    tx.Save(&User{})
    tx.Save(&Order{})
    tx.Delete(&Order{})
    tx.Commit()
}
