#!/bin/bash

# Script to update Shares.js with better validation

cd /opt/moxnas/frontend/src/pages

# Backup original file
cp Shares.js Shares.js.backup

# Add duplicate name validation
sed -i '/\/\/ Validate required fields/,/return;/{
  /return;/a\
\
      // Check for duplicate share names (when creating new share)\
      if (!editingShare) {\
        const existingShare = shares.find(share => \
          share.name.toLowerCase() === formData.name.toLowerCase()\
        );\
        if (existingShare) {\
          alert(`A share named "${formData.name}" already exists. Please choose a different name.`);\
          return;\
        }\
      }
}' Shares.js

# Improve error handling
sed -i '/} catch (error) {/,/alert(`Error: \${errorMessage}`);/{
  s/} catch (error) {/} catch (error) {\
      console.error('\''Error saving share:'\'', error);\
\
      \/\/ Enhanced error handling with specific messages\
      let errorMessage = '\''Failed to save share'\'';\
\
      if (error.response?.status === 400) {\
        if (error.response?.data?.name) {\
          errorMessage = `Share name error: ${error.response.data.name[0]}`;\
        } else if (error.response?.data?.non_field_errors) {\
          errorMessage = error.response.data.non_field_errors[0];\
        } else {\
          errorMessage = '\''Invalid data provided. Please check all fields.'\'';\
        }\
      } else if (error.response?.status === 500) {\
        errorMessage = '\''Server error occurred while creating the share. Please try again.'\'';\
      } else if (error.response?.data?.error) {\
        errorMessage = error.response.data.error;\
      } else if (error.message) {\
        errorMessage = error.message;\
      }/
}' Shares.js

echo "✅ Shares.js validation improvements applied"
echo "📍 Original file backed up as Shares.js.backup"