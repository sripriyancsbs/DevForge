package main

import (
	"fmt"
	"net/http"
	"os"

	"github.com/gin-gonic/gin"
)

func setupRouter() *gin.Engine {
	gin.SetMode(gin.ReleaseMode)
	r := gin.New()
	r.Use(gin.Recovery())

	// Health check endpoint
	r.GET("/healthz", func(c *gin.Context) {
		c.JSON(http.StatusOK, gin.H{
			"status":      "healthy",
			"service":     "{{APPLICATION_NAME}}",
			"environment": "{{ENVIRONMENT}}",
		})
	})

	// Legacy /health alias
	r.GET("/health", func(c *gin.Context) {
		c.JSON(http.StatusOK, gin.H{
			"status":      "healthy",
			"service":     "{{APPLICATION_NAME}}",
			"environment": "{{ENVIRONMENT}}",
		})
	})

	// Root endpoint
	r.GET("/", func(c *gin.Context) {
		c.JSON(http.StatusOK, gin.H{
			"message": "Go Gin API service {{APPLICATION_NAME}} running on DevForge IDP",
			"version": "{{VERSION}}",
		})
	})

	return r
}

func main() {
	port := os.Getenv("PORT")
	if port == "" {
		port = "{{PORT}}"
	}

	r := setupRouter()
	fmt.Printf("[DevForge] {{APPLICATION_NAME}} Go Gin server listening on port %s\n", port)
	r.Run(":" + port)
}
